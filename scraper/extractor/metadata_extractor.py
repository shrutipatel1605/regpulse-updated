"""Metadata extraction from RBI circular raw text.

Standalone scraper module. NEVER imports from backend/app/.
Extracts circular_number, issued_date, department, effective_date,
action_deadline, affected_teams, supersession_refs from raw text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import structlog

from scraper.extractor.constants import (
    ACTION_DEADLINE_TRIGGERS,
    RBI_DEPARTMENTS,
    SUPERSESSION_PATTERNS,
    TEAM_KEYWORDS,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.metadata")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CircularMetadata:
    """Extracted metadata from an RBI circular."""

    circular_number: str | None = None
    department: str | None = None
    department_code: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    action_deadline: date | None = None
    affected_teams: list[str] = field(default_factory=list)
    supersession_refs: list[str] = field(default_factory=list)
    confidence_score: float = 0.0


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

# Month name → number
_MONTH_MAP: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Multiple date format regexes — ordered by specificity
# "March 10, 2026" or "March 10,2026"
_DATE_LONG_MDY = re.compile(
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r")\s+(\d{1,2})\s*,\s*(\d{4})\b",
    re.IGNORECASE,
)

# "10 March 2026" or "10th March 2026"
_DATE_LONG_DMY = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r")\s+(\d{4})\b",
    re.IGNORECASE,
)

# "10-03-2026" or "10/03/2026" (DD-MM-YYYY)
_DATE_NUMERIC_DMY = re.compile(r"\b(\d{2})[-/](\d{2})[-/](\d{4})\b")

# "2026-03-10" (ISO format)
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Short month: "10 Mar 2026", "Mar 10, 2026"
_DATE_SHORT_DMY = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
    r"(?:\.|\b)\s*,?\s*(\d{4})\b",
    re.IGNORECASE,
)
_DATE_SHORT_MDY = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
    r"(?:\.|\b)\s*(\d{1,2})\s*,\s*(\d{4})\b",
    re.IGNORECASE,
)


def _parse_date_match_long_mdy(m: re.Match[str]) -> date | None:
    """Parse 'March 10, 2026' format."""
    month_num = _MONTH_MAP.get(m.group(1).lower())
    if month_num is None:
        return None
    try:
        return date(int(m.group(3)), month_num, int(m.group(2)))
    except ValueError:
        return None


def _parse_date_match_long_dmy(m: re.Match[str]) -> date | None:
    """Parse '10 March 2026' format."""
    month_num = _MONTH_MAP.get(m.group(2).lower())
    if month_num is None:
        return None
    try:
        return date(int(m.group(3)), month_num, int(m.group(1)))
    except ValueError:
        return None


def _parse_date_match_numeric_dmy(m: re.Match[str]) -> date | None:
    """Parse '10-03-2026' or '10/03/2026' format."""
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _parse_date_match_iso(m: re.Match[str]) -> date | None:
    """Parse '2026-03-10' format."""
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _parse_date_match_short_dmy(m: re.Match[str]) -> date | None:
    """Parse '10 Mar 2026' format."""
    month_num = _MONTH_MAP.get(m.group(2).lower())
    if month_num is None:
        return None
    try:
        return date(int(m.group(3)), month_num, int(m.group(1)))
    except ValueError:
        return None


def _parse_date_match_short_mdy(m: re.Match[str]) -> date | None:
    """Parse 'Mar 10, 2026' format."""
    month_num = _MONTH_MAP.get(m.group(1).lower())
    if month_num is None:
        return None
    try:
        return date(int(m.group(3)), month_num, int(m.group(2)))
    except ValueError:
        return None


def _find_all_dates(text: str) -> list[tuple[date, int]]:
    """Find all dates in text with their character positions.

    Returns list of (date, position) sorted by position.
    """
    results: list[tuple[date, int]] = []

    for m in _DATE_LONG_MDY.finditer(text):
        d = _parse_date_match_long_mdy(m)
        if d:
            results.append((d, m.start()))

    for m in _DATE_LONG_DMY.finditer(text):
        d = _parse_date_match_long_dmy(m)
        if d:
            results.append((d, m.start()))

    for m in _DATE_SHORT_MDY.finditer(text):
        d = _parse_date_match_short_mdy(m)
        if d:
            results.append((d, m.start()))

    for m in _DATE_SHORT_DMY.finditer(text):
        d = _parse_date_match_short_dmy(m)
        if d:
            results.append((d, m.start()))

    for m in _DATE_NUMERIC_DMY.finditer(text):
        d = _parse_date_match_numeric_dmy(m)
        if d:
            results.append((d, m.start()))

    for m in _DATE_ISO.finditer(text):
        d = _parse_date_match_iso(m)
        if d:
            results.append((d, m.start()))

    # Deduplicate by (date, position) and sort by position
    seen: set[tuple[date, int]] = set()
    unique: list[tuple[date, int]] = []
    for item in results:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    unique.sort(key=lambda x: x[1])
    return unique


def _find_date_near_pattern(text: str, pattern: re.Pattern[str]) -> date | None:
    """Find the first date occurring within 200 chars after a pattern match."""
    for m in pattern.finditer(text):
        # Look for dates in the 200-char window after the trigger phrase
        window_start = m.start()
        window_end = min(m.end() + 200, len(text))
        window = text[window_start:window_end]
        dates = _find_all_dates(window)
        if dates:
            return dates[0][0]
    return None


# ---------------------------------------------------------------------------
# Circular number extraction
# ---------------------------------------------------------------------------

# RBI/YYYY-YY/NNN format (primary)
_CIRCULAR_NUMBER_RE = re.compile(
    r"\bRBI/\d{4}-\d{2}/\d{1,4}\b",
)

# Department reference: DOR.MRG.REC.No.436/21-01-002/2025-26
_DEPT_REF_RE = re.compile(
    r"\b([A-Z]{2,6})(?:\.[A-Z]{2,6})*\.(?:REC|No|Ref)\.\s*(?:No\.)?\s*[\w./-]+/\d{4}-\d{2,4}\b",
)


# ---------------------------------------------------------------------------
# MetadataExtractor
# ---------------------------------------------------------------------------


class MetadataExtractor:
    """Extract structured metadata from RBI circular raw text.

    Extracts: circular_number, department, issued_date, effective_date,
    action_deadline, affected_teams, supersession_refs.
    All fields are Optional. Returns CircularMetadata with confidence_score.
    """

    def extract(self, raw_text: str, source_url: str = "") -> CircularMetadata:
        """Extract metadata from raw circular text.

        Args:
            raw_text: Full text from PDFExtractor (includes "--- Page N ---" markers).
            source_url: Original RBI URL (used for logging, not for extraction).

        Returns:
            CircularMetadata with all extractable fields populated.
        """
        # Work with first 3 pages for header metadata (circular number, department, dates)
        header_text = self._get_header_text(raw_text)

        circular_number = self._extract_circular_number(header_text)
        department, department_code = self._extract_department(header_text)
        issued_date = self._extract_issued_date(header_text)
        effective_date = self._extract_effective_date(raw_text)
        action_deadline = self._extract_action_deadline(raw_text)
        affected_teams = self._extract_affected_teams(raw_text)
        supersession_refs = self._extract_supersession_refs(raw_text)

        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            circular_number=circular_number,
            department=department,
            issued_date=issued_date,
            effective_date=effective_date,
        )

        result = CircularMetadata(
            circular_number=circular_number,
            department=department,
            department_code=department_code,
            issued_date=issued_date,
            effective_date=effective_date,
            action_deadline=action_deadline,
            affected_teams=affected_teams,
            supersession_refs=supersession_refs,
            confidence_score=confidence_score,
        )

        logger.info(
            "metadata_extracted",
            source_url=source_url,
            circular_number=circular_number,
            department=department,
            issued_date=str(issued_date) if issued_date else None,
            effective_date=str(effective_date) if effective_date else None,
            action_deadline=str(action_deadline) if action_deadline else None,
            affected_teams=affected_teams,
            supersession_refs_count=len(supersession_refs),
            confidence=confidence_score,
        )

        return result

    # ------------------------------------------------------------------
    # Private extraction methods
    # ------------------------------------------------------------------

    @staticmethod
    def _get_header_text(raw_text: str) -> str:
        """Get text from the first 3 pages (where metadata usually lives)."""
        pages = raw_text.split("--- Page ")
        # Take pages 1-3 (index 0 is empty or pre-first-marker text)
        header_parts = pages[:4]  # includes any text before first marker
        return "\n".join(header_parts)

    @staticmethod
    def _extract_circular_number(text: str) -> str | None:
        """Extract RBI circular number (e.g. RBI/2025-26/241)."""
        match = _CIRCULAR_NUMBER_RE.search(text)
        if match:
            return match.group(0)
        return None

    @staticmethod
    def _extract_department(text: str) -> tuple[str | None, str | None]:
        """Extract department name from department reference code.

        Returns (full_department_name, department_code).
        """
        match = _DEPT_REF_RE.search(text)
        if match:
            dept_code = match.group(1)
            full_name = RBI_DEPARTMENTS.get(dept_code)
            if full_name:
                return full_name, dept_code
            return None, dept_code

        # Fallback: scan for known department abbreviations in text
        text_upper = text.upper()
        for code, name in RBI_DEPARTMENTS.items():
            if code in text_upper:
                return name, code
        return None, None

    
    @staticmethod
    def _extract_issued_date(header_text: str) -> date | None:
        """Extract the actual issuance/publication date from an RBI circular.

        RBI circulars commonly place the issuance date immediately after
        the department/reference number, e.g.:

            DOR.SOG(SPE).REC.214/13.03.00/2026-27 August 25, 2026

        This must take precedence over dates mentioned later in the document,
        such as dates of earlier circulars referenced in the text.
        """

        # ---------------------------------------------------------------
        # Strategy 1: RBI header reference followed by the issue date
        #
        # Example:
        # DOR.SOG(SPE).REC.214/13.03.00/2026-27 August 25, 2026
        # ---------------------------------------------------------------

        header_date_re = re.compile(
            r"(?:"
            r"[A-Z]{2,10}"
            r"(?:\.[A-Z0-9()\-]+)+"
            r"\s*"
            r"(?:No\.)?"
            r"[\w./()\-]+"
            r"/\d{4}-\d{2}"
            r")"
            r"\s+"
            r"("
            r"(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)"
            r"\s+\d{1,2}\s*,\s*\d{4}"
            r")",
            re.IGNORECASE,
        )

        match = header_date_re.search(header_text)

        if match:
            date_text = match.group(1)
            parsed_dates = _find_all_dates(date_text)

            if parsed_dates:
                logger.debug(
                    "issued_date_from_rbi_header",
                    issued_date=str(parsed_dates[0][0]),
                )
                return parsed_dates[0][0]

        # ---------------------------------------------------------------
        # Strategy 2: Look for the circular number followed by a date.
        #
        # Example:
        # RBI/2026-27/248
        # DOR.... August 25, 2026
        # ---------------------------------------------------------------

        circular_match = _CIRCULAR_NUMBER_RE.search(header_text)

        if circular_match:
            # Only inspect a limited window after the circular number.
            # This prevents dates from referenced older circulars from
            # being selected.
            window_start = circular_match.start()
            window_end = min(window_start + 500, len(header_text))
            window = header_text[window_start:window_end]

            dates = _find_all_dates(window)

            if dates:
                return dates[0][0]

        # ---------------------------------------------------------------
        # Strategy 3: Look for a date immediately before the title.
        #
        # This handles RBI documents where the department reference/date
        # formatting differs slightly.
        # ---------------------------------------------------------------

        title_patterns = [
            re.compile(
                r"\bDirections\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bCircular\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bNotification\b",
                re.IGNORECASE,
            ),
        ]

        for title_pattern in title_patterns:
            title_match = title_pattern.search(header_text)

            if title_match:
                before_title = header_text[:title_match.start()]

                # Look only at the previous 300 characters.
                window = before_title[-300:]

                dates = _find_all_dates(window)

                if dates:
                    return dates[-1][0]

        # ---------------------------------------------------------------
        # Strategy 4: Only now use "dated <date>".
        #
        # This is deliberately LAST because "dated" often refers to an
        # older circular referenced by the current circular.
        # ---------------------------------------------------------------

        dated_patterns = [
            re.compile(
                r"\bdated\s*[:\-]?\s*"
                r"((?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)"
                r"\s+\d{1,2}\s*,\s*\d{4})",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bdated\s*[:\-]?\s*"
                r"(\d{1,2}(?:st|nd|rd|th)?\s+"
                r"(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)"
                r"\s+\d{4})",
                re.IGNORECASE,
            ),
        ]

        for pattern in dated_patterns:
            match = pattern.search(header_text)

            if match:
                parsed_dates = _find_all_dates(match.group(1))

                if parsed_dates:
                    return parsed_dates[0][0]

        # ---------------------------------------------------------------
        # Strategy 5: Final fallback — first date in the header.
        # ---------------------------------------------------------------

        dates = _find_all_dates(header_text)

        if dates:
            return dates[0][0]

        return None

    @staticmethod
    def _extract_effective_date(text: str) -> date | None:
        """Extract the effective/operative date of the circular."""
        effective_re = re.compile(
            r"(?:effective|operative|applicable|come\s+into\s+(?:force|effect))"
            r"\s+(?:from|on|w\.?e\.?f\.?)",
            re.IGNORECASE,
        )

        d = _find_date_near_pattern(text, effective_re)

        if d:
            return d

        # Try "w.e.f." (with effect from) — common RBI abbreviation
        wef_re = re.compile(r"\bw\.?e\.?f\.?\b", re.IGNORECASE)

        d = _find_date_near_pattern(text, wef_re)

        if d:
            return d

        return None
    
    @staticmethod
    def _extract_action_deadline(text: str) -> date | None:
        """Extract action deadline — distinct from effective_date.

        Scans for trigger phrases like 'last date', 'submit by', 'on or before',
        'implement by' followed by date patterns.
        """
        for pattern_str in ACTION_DEADLINE_TRIGGERS:
            trigger_re = re.compile(pattern_str, re.IGNORECASE)
            d = _find_date_near_pattern(text, trigger_re)
            if d:
                # Sanity check: deadline should be a reasonable future-ish date
                # (not before year 2000 and not after 2100)
                if date(2000, 1, 1) <= d <= date(2100, 1, 1):
                    return d
        return None

    @staticmethod
    def _extract_affected_teams(text: str) -> list[str]:
        """Classify which teams are affected based on keyword matching.

        Uses the TEAM_KEYWORDS taxonomy from constants.py.
        Returns sorted list of team names that match.
        """
        text_lower = text.lower()
        matched_teams: list[str] = []

        for team, keywords in TEAM_KEYWORDS.items():
            hit_count = sum(1 for kw in keywords if kw in text_lower)
            # Require at least 2 keyword hits to reduce false positives
            if hit_count >= 2:
                matched_teams.append(team)

        # Always include Compliance for RBI circulars (they're all regulatory)
        if "Compliance" not in matched_teams:
            matched_teams.append("Compliance")

        matched_teams.sort()
        return matched_teams

    @staticmethod
    def _extract_supersession_refs(text: str) -> list[str]:
        """Extract references to superseded/replaced circulars.

        Finds supersession trigger phrases and then looks for nearby
        circular numbers (RBI/YYYY-YY/NNN format).
        """
        refs: list[str] = []

        for pattern_str in SUPERSESSION_PATTERNS:
            trigger_re = re.compile(pattern_str, re.IGNORECASE)
            for m in trigger_re.finditer(text):
                # Search for circular numbers within 300 chars after the trigger
                window_start = m.start()
                window_end = min(m.end() + 300, len(text))
                window = text[window_start:window_end]
                for cn_match in _CIRCULAR_NUMBER_RE.finditer(window):
                    cn = cn_match.group(0)
                    if cn not in refs:
                        refs.append(cn)

        return refs

    @staticmethod
    def _calculate_confidence(
        circular_number: str | None,
        department: str | None,
        issued_date: date | None,
        effective_date: date | None,
    ) -> float:
        """Calculate a confidence score (0.0–1.0) based on how many fields extracted."""
        score = 0.0
        total_weight = 0.0

        # Circular number — most important
        total_weight += 0.4
        if circular_number:
            score += 0.4

        # Department
        total_weight += 0.2
        if department:
            score += 0.2

        # Issued date
        total_weight += 0.25
        if issued_date:
            score += 0.25

        # Effective date (less critical — many circulars are effective immediately)
        total_weight += 0.15
        if effective_date:
            score += 0.15

        return round(score / total_weight, 2) if total_weight > 0 else 0.0
