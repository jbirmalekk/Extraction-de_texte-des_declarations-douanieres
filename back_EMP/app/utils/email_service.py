import smtplib
from email.message import EmailMessage
from typing import Optional
from ..config import settings


def send_email_verification(to_email: str, verification_token: str, frontend_url: Optional[str] = None) -> None:
    """Envoie un email de vérification d'adresse email via SMTP (Mailtrap)."""
    verify_link = f"{frontend_url or settings.FRONTEND_URL}/verify-email?token={verification_token}"

    msg = EmailMessage()
    msg["Subject"] = "Vérifiez votre adresse email"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333; text-align: center;">Bienvenue sur EMP SmartOCR! 🎉</h2>
                <p style="color: #555; font-size: 16px; line-height: 1.6;">
                    Bonjour,
                </p>
                <p style="color: #555; font-size: 16px; line-height: 1.6;">
                    Merci de vous être inscrit! Pour activer votre compte et commencer à utiliser notre plateforme, 
                    veuillez confirmer votre adresse email en cliquant sur le bouton ci-dessous:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verify_link}" style="display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                        Vérifier mon email
                    </a>
                </div>
                <p style="color: #999; font-size: 12px;">
                    Si le bouton ne fonctionne pas, copiez et collez ce lien dans votre navigateur:
                </p>
                <p style="color: #4F46E5; font-size: 12px; word-break: break-all;">
                    {verify_link}
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    Ce lien de vérification expire dans <strong>24 heures</strong>.
                </p>
                <p style="color: #999; font-size: 12px;">
                    Si vous n'avez pas créé ce compte, veuillez ignorer cet email.
                </p>
                <p style="color: #999; font-size: 12px; text-align: center; margin-top: 30px;">
                    © 2026 EMP SmartOCR. Tous droits réservés.
                </p>
            </div>
        </body>
    </html>
    """
    
    msg.set_content("Veuillez confirmer votre email en cliquant sur le lien fourni.")
    msg.add_alternative(html_content, subtype='html')

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def send_approval_notification(to_email: str, is_approved: bool) -> None:
    """Envoie un email de notification d'approbation du compte par l'admin."""
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    if is_approved:
        msg["Subject"] = "Votre compte a été approuvé"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #22C55E; text-align: center;">✓ Compte Approuvé!</h2>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Bonjour,
                    </p>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Bonne nouvelle! Votre compte a été <strong>approuvé par un administrateur</strong>.
                    </p>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Vous pouvez maintenant vous connecter à EMP SmartOCR et commencer à utiliser la plateforme.
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{settings.FRONTEND_URL}/login" style="display: inline-block; padding: 12px 30px; background-color: #22C55E; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                            Se Connecter
                        </a>
                    </div>
                    <p style="color: #999; font-size: 12px; text-align: center; margin-top: 30px;">
                        © 2026 EMP SmartOCR. Tous droits réservés.
                    </p>
                </div>
            </body>
        </html>
        """
        msg.set_content("Votre compte a été approuvé! Vous pouvez maintenant vous connecter.")
        msg.add_alternative(html_content, subtype='html')
    else:
        msg["Subject"] = "Votre demande d'inscription a été rejetée"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #EF4444; text-align: center;">Demande Rejetée</h2>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Bonjour,
                    </p>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Malheureusement, votre demande d'inscription a été <strong>rejetée</strong> par nos administrateurs.
                    </p>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Si vous avez des questions concernant cette décision, veuillez nous contacter.
                    </p>
                    <p style="color: #999; font-size: 12px; text-align: center; margin-top: 30px;">
                        © 2026 EMP SmartOCR. Tous droits réservés.
                    </p>
                </div>
            </body>
        </html>
        """
        msg.set_content("Votre demande d'inscription a été rejetée.")
        msg.add_alternative(html_content, subtype='html')

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


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
