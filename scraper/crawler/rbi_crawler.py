from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse
import re

import httpx
import structlog
from bs4 import BeautifulSoup


logger = structlog.get_logger(__name__)

_RBI_BASE_URL = "https://www.rbi.org.in"
_RBI_DOCS_HOST = "rbidocs.rbi.org.in"


RBI_SECTIONS = {
    "Notifications": f"{_RBI_BASE_URL}/Scripts/NotificationUser.aspx",
    "Master Directions": f"{_RBI_BASE_URL}/Scripts/BS_ViewMasterDirections.aspx",
}


@dataclass
class RBIDocumentLink:
    title: str
    url: str
    doc_type: str
    published_date: Optional[datetime] = None


class RBICrawler:
    def __init__(self) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.4 Safari/605.1.15"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.rbi.org.in/",
        }

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def fetch_page(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            headers=self.headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            logger.info(
                "rbi_page_fetched",
                url=str(response.url),
                status=response.status_code,
                content_type=response.headers.get("content-type"),
                bytes=len(response.content),
            )

            return response.text

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_pdf_url(url: str) -> bool:
        parsed = urlparse(url)

        if parsed.netloc.lower() != _RBI_DOCS_HOST:
            return False

        path = parsed.path.lower()

        return (
            path.endswith(".pdf")
            and "/rdocs/notification/pdfs/" in path
        )

    # ------------------------------------------------------------------
    # Text / date helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.split()).strip()

    @staticmethod
    def _clean_title(title: str) -> str:
        """
        RBI PDF anchor text often looks like:

            Some Notification 222 kb

        Remove the trailing file-size information.
        """

        title = " ".join(title.split())

        title = re.sub(
            r"\s*\(?\d+(?:\.\d+)?\s*(?:kb|mb)\)?\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        )

        return title.strip()

    @staticmethod
    def _parse_date(text: str) -> Optional[datetime]:
        text = " ".join(text.split())

        formats = [
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def _extract_date_from_text(text: str) -> Optional[datetime]:
        """
        Extract dates such as:

            Aug 25, 2026
            August 25, 2026
            25 Aug 2026
            25 August 2026
        """

        text = " ".join(text.split())

        patterns = [
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+\d{1,2},\s+\d{4}\b",

            r"\b(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)"
            r"\s+\d{1,2},\s+\d{4}\b",

            r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
            r"Nov|Dec)\s+\d{4}\b",

            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|"
            r"July|August|September|October|November|December)\s+\d{4}\b",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:
                parsed = RBICrawler._parse_date(match.group(0))

                if parsed:
                    return parsed

        return None

    # ------------------------------------------------------------------
    # Notification extraction
    # ------------------------------------------------------------------

    def _extract_notification_links(
        self,
        html: str,
    ) -> list[RBIDocumentLink]:

        soup = BeautifulSoup(html, "html.parser")

        links: list[RBIDocumentLink] = []

        # RBI notification pages contain a sequence of:
        #
        #   notification detail link
        #   title/date information
        #   direct PDF link
        #
        # We remember the most recent notification title/date and attach
        # them to the next direct PDF.

        current_title: Optional[str] = None
        current_date: Optional[datetime] = None

        for anchor in soup.find_all("a", href=True):

            href = anchor.get("href", "").strip()

            if not href:
                continue

            absolute_url = urljoin(
                _RBI_BASE_URL + "/",
                href,
            )

            # ==========================================================
            # 1. DIRECT PDF
            # ==========================================================

            if self._is_pdf_url(absolute_url):

                raw_title = self._clean_text(
                    anchor.get_text(" ", strip=True)
                )

                title = self._clean_title(raw_title)

                # ------------------------------------------------------
                # Find surrounding row/container
                # ------------------------------------------------------

                row = anchor.find_parent("tr")

                if row:
                    row_text = self._clean_text(
                        row.get_text(" ", strip=True)
                    )

                    # Try to extract date from the row.
                    row_date = self._extract_date_from_text(
                        row_text
                    )

                    if row_date:
                        current_date = row_date

                    # If the PDF anchor only contains the file size,
                    # try to recover the title from the row.
                    if not title:
                        row_links = row.find_all("a", href=True)

                        for row_anchor in row_links:
                            row_href = row_anchor.get(
                                "href",
                                "",
                            )

                            if "NotificationUser.aspx" in row_href:
                                possible_title = self._clean_text(
                                    row_anchor.get_text(
                                        " ",
                                        strip=True,
                                    )
                                )

                                if possible_title:
                                    title = self._clean_title(
                                        possible_title
                                    )
                                    break

                # ------------------------------------------------------
                # Fallback to current notification metadata
                # ------------------------------------------------------

                if not title:
                    title = current_title

                if not title:
                    title = "RBI Notification"

                published_date = current_date

                document = RBIDocumentLink(
                    title=title,
                    url=absolute_url,
                    doc_type="notification",
                    published_date=published_date,
                )

                links.append(document)

                logger.debug(
                    "rbi_pdf_found",
                    title=title,
                    url=absolute_url,
                    published_date=published_date,
                )

                # This PDF belongs to the current notification.
                current_title = None
                current_date = None

                continue

            # ==========================================================
            # 2. NOTIFICATION DETAIL LINK
            # ==========================================================

            parsed = urlparse(absolute_url)

            is_notification_detail = (
                parsed.netloc.lower() == "www.rbi.org.in"
                and parsed.path.lower().endswith(
                    "/notificationuser.aspx"
                )
                and "id=" in parsed.query.lower()
            )

            if is_notification_detail:

                title = self._clean_text(
                    anchor.get_text(
                        " ",
                        strip=True,
                    )
                )

                if title:
                    current_title = self._clean_title(title)

                # ------------------------------------------------------
                # Look for date in the surrounding row.
                # ------------------------------------------------------

                row = anchor.find_parent("tr")

                if row:
                    row_text = self._clean_text(
                        row.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    found_date = self._extract_date_from_text(
                        row_text
                    )

                    if found_date:
                        current_date = found_date

                # ------------------------------------------------------
                # Also inspect nearby parent containers.
                # ------------------------------------------------------

                if current_date is None:

                    container = (
                        anchor.find_parent("td")
                        or anchor.parent
                    )

                    if container:

                        container_text = self._clean_text(
                            container.get_text(
                                " ",
                                strip=True,
                            )
                        )

                        found_date = (
                            self._extract_date_from_text(
                                container_text
                            )
                        )

                        if found_date:
                            current_date = found_date

                continue

        logger.info(
            "links_extracted",
            section="Notifications",
            count=len(links),
            url=RBI_SECTIONS["Notifications"],
        )

        return links

    # ------------------------------------------------------------------
    # Master Directions
    # ------------------------------------------------------------------

    def _extract_master_direction_links(
        self,
        html: str,
    ) -> list[RBIDocumentLink]:

        soup = BeautifulSoup(html, "html.parser")

        links: list[RBIDocumentLink] = []

        for anchor in soup.find_all("a", href=True):

            href = anchor.get("href", "").strip()

            if not href:
                continue

            absolute_url = urljoin(
                _RBI_BASE_URL + "/",
                href,
            )

            if not self._is_pdf_url(absolute_url):
                continue

            title = self._clean_title(
                self._clean_text(
                    anchor.get_text(
                        " ",
                        strip=True,
                    )
                )
            )

            if not title:

                row = anchor.find_parent("tr")

                if row:
                    title = self._clean_title(
                        self._clean_text(
                            row.get_text(
                                " ",
                                strip=True,
                            )
                        )
                    )

            if not title:
                title = "RBI Master Direction"

            links.append(
                RBIDocumentLink(
                    title=title,
                    url=absolute_url,
                    doc_type="master_direction",
                    published_date=None,
                )
            )

        logger.info(
            "links_extracted",
            section="Master Directions",
            count=len(links),
            url=RBI_SECTIONS["Master Directions"],
        )

        return links

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_document_links(
        self,
        section_name: str,
    ) -> list[RBIDocumentLink]:

        if section_name not in RBI_SECTIONS:
            raise ValueError(
                f"Unknown RBI section: {section_name}"
            )

        url = RBI_SECTIONS[section_name]

        html = await self.fetch_page(url)

        if section_name == "Notifications":
            return self._extract_notification_links(html)

        if section_name == "Master Directions":
            return self._extract_master_direction_links(html)

        return []

    async def crawl(
        self,
        sections: Optional[list[str]] = None,
    ) -> list[RBIDocumentLink]:

        if sections is None:
            sections = list(RBI_SECTIONS.keys())

        all_documents: list[RBIDocumentLink] = []

        for section in sections:

            try:

                documents = await self.fetch_document_links(
                    section
                )

                all_documents.extend(documents)

                logger.info(
                    "new_documents_found",
                    section=section,
                    total=len(documents),
                )

            except Exception as exc:

                logger.exception(
                    "rbi_section_failed",
                    section=section,
                    error=str(exc),
                )

        # De-duplicate by URL.
        unique: dict[str, RBIDocumentLink] = {}

        for document in all_documents:
            unique[document.url] = document

        result = list(unique.values())

        logger.info(
            "crawl_complete",
            total_new=len(result),
        )

        return result


# ----------------------------------------------------------------------
# Manual test
# ----------------------------------------------------------------------

async def main() -> None:

    crawler = RBICrawler()

    documents = await crawler.fetch_document_links(
        "Notifications"
    )

    print("=" * 100)
    print("DISCOVERED RBI DOCUMENTS")
    print("=" * 100)

    for document in documents[:30]:

        print()
        print("TITLE:", document.title)
        print("URL:", document.url)
        print("TYPE:", document.doc_type)
        print("DATE:", document.published_date)

    print()
    print("=" * 100)
    print("TOTAL DOCUMENTS:", len(documents))
    print("=" * 100)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())