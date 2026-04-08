import smtplib
from email.message import EmailMessage
from typing import Optional
from ..config import settings


def send_reset_email(to_email: str, reset_token: str, frontend_url: Optional[str] = None) -> None:
    """Envoie un email de reset de mot de passe via SMTP (Mailtrap)."""
    reset_link = f"{frontend_url or settings.FRONTEND_URL}/reset-password?token={reset_token}"

    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Hello,\n\nTo reset your password, click the link below:\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
