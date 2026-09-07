"""Email delivery service using aiosmtplib and Jinja2 templates.

Only domain names are logged — never full email addresses (PII protection).
OTP values are never logged.
"""

from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


class EmailService:
    """Send transactional emails via SMTP with Jinja2 HTML templates."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._jinja = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_otp_email(
        self,
        to_email: str,
        otp: str,
        purpose: str = "login",
    ) -> None:
        """Send an OTP email using the appropriate template for the purpose."""
        template_map = {
            "register": "register_otp.html",
            "login": "login_otp.html",
        }
        template_name = template_map.get(purpose, "login_otp.html")
        subject_map = {
            "register": "RegPulse — Verify your email",
            "login": "RegPulse — Your login code",
        }
        subject = subject_map.get(purpose, "RegPulse — Your verification code")

        expiry = self._settings.OTP_EXPIRY_MINUTES
        html = self._render(template_name, otp=otp, expiry_minutes=expiry)
        plain = f"Your RegPulse verification code is: {otp}\n" f"This code expires in {expiry} minutes."

        await self.send_html_email(to_email, subject, html, plain)

    async def send_welcome_email(self, to_email: str, full_name: str) -> None:
        """Send welcome email after successful registration."""
        html = self._render("welcome.html", full_name=full_name)
        plain = f"Welcome to RegPulse, {full_name}! Your account is ready."
        await self.send_html_email(to_email, "Welcome to RegPulse!", html, plain)

    async def send_payment_success_email(
        self,
        to_email: str,
        plan_name: str,
        credits_added: int,
    ) -> None:
        """Send payment confirmation email."""
        html = self._render(
            "payment_success.html",
            plan_name=plan_name,
            credits_added=credits_added,
        )
        plain = f"Payment received! Your {plan_name} plan is active with {credits_added} credits."
        await self.send_html_email(to_email, "RegPulse — Payment confirmed", html, plain)

    async def send_low_credits_email(
        self,
        to_email: str,
        remaining_credits: int,
    ) -> None:
        """Send low-credits warning email."""
        html = self._render("low_credits.html", remaining_credits=remaining_credits)
        plain = f"You have {remaining_credits} credit(s) remaining on RegPulse. " "Upgrade to continue asking questions."
        await self.send_html_email(to_email, "RegPulse — Low credit balance", html, plain)

    async def send_staleness_alert_email(
        self,
        to_email: str,
        circular_number: str,
        interpretation_name: str,
    ) -> None:
        """Notify user that a saved interpretation may be stale."""
        html = self._render(
            "staleness_alert.html",
            circular_number=circular_number,
            interpretation_name=interpretation_name,
        )
        plain = f'Your saved interpretation "{interpretation_name}" references circular ' f"{circular_number}, which has been updated. Please review."
        await self.send_html_email(to_email, "RegPulse — Saved interpretation needs review", html, plain)

    async def send_html_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> None:
        """Send an HTML email with optional plain-text fallback via SMTP."""
        domain = to_email.rsplit("@", 1)[-1] if "@" in to_email else "unknown"

        msg = MIMEMultipart("alternative")
        msg["From"] = self._settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject

        if plain_body:
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USER,
                password=self._settings.SMTP_PASS,
                use_tls=True,
            )
            logger.info("email_sent", domain=domain, subject=subject)
        except Exception:
            logger.exception("email_send_failed", domain=domain, subject=subject)
            raise

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _render(self, template_name: str, **ctx: object) -> str:
        """Render a Jinja2 template with the given context."""
        tmpl = self._jinja.get_template(template_name)
        return tmpl.render(**ctx)
