"""SMTP email service — weekly digest and transactional alerts."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

log = logging.getLogger(__name__)

_jinja = Environment(
    loader=FileSystemLoader("app/templates/email"),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, context: dict) -> tuple[str, str]:
    """Return (html_body, plain_text_body) for a template."""
    html = _jinja.get_template(f"{template_name}.html").render(**context)
    try:
        plain = _jinja.get_template(f"{template_name}.txt").render(**context)
    except Exception:
        plain = ""
    return html, plain


def send_email(to: str, subject: str, html: str, plain: str = "") -> bool:
    """Send email via SMTP. Returns True on success."""
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        log.debug("SMTP not configured — skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Blackout Predictor <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to

    if plain:
        msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
        log.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as exc:
        log.error(f"SMTP error sending to {to}: {exc}")
        return False


def send_weekly_digest_email(
    to: str,
    area: str,
    outages_last_week: int,
    outages_by_day: list[dict],
    predictions_this_week: int,
    high_risk_windows: list[dict],
    unsubscribe_url: str,
) -> bool:
    context = {
        "area": area,
        "outages_last_week": outages_last_week,
        "outages_by_day": outages_by_day,
        "predictions_this_week": predictions_this_week,
        "high_risk_windows": high_risk_windows,
        "unsubscribe_url": unsubscribe_url,
        "app_url": settings.APP_URL,
    }
    html, plain = _render("weekly_digest", context)
    trend = "more" if predictions_this_week > outages_last_week else "fewer"
    subject = f"⚡ Your weekly outage digest — {trend} outages expected this week"
    return send_email(to, subject, html, plain)
