"""
Outgoing email (invite links, etc). Uses smtplib (stdlib -- no extra
dependency) against whatever SMTP_* settings are configured in .env.
Gracefully no-ops when unconfigured: logs a warning and returns False,
rather than crashing the request that triggered the email. Callers use
that return value to decide what to show the user (e.g. the invite
endpoint returns the raw invite link in dev when no email actually went out).
"""
import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning("SMTP not configured -- skipping email to %s (subject=%r)", to, subject)
        return False

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
            server.sendmail(settings.SMTP_FROM_EMAIL, [to], message.as_string())
        return True
    except Exception:  # noqa: BLE001 -- email delivery must never break the calling request
        logger.exception("Failed to send email to %s", to)
        return False


def send_invite_email(*, to: str, full_name: str, invite_link: str, tenant_name: str) -> bool:
    subject = f"You've been invited to {tenant_name} on UtilityOS"
    body = (
        f"Hi {full_name},\n\n"
        f"You've been invited to join {tenant_name} on UtilityOS. Click the link below to set your password "
        f"and activate your account:\n\n{invite_link}\n\n"
        f"This link expires in {settings.INVITE_TOKEN_EXPIRE_DAYS} days.\n\n"
        f"If you weren't expecting this invite, you can ignore this email."
    )
    return send_email(to=to, subject=subject, body=body)
