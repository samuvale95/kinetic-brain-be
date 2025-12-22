from typing import Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy.orm import Session
from app.services.email_config_service import EmailConfigService
from loguru import logger


class EmailService:
    """
    Service for sending emails using fastapi-mail.
    Configuration is loaded dynamically from database or environment variables.
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize email service.
        
        Args:
            db: Optional database session for loading configuration from database
        """
        self.db = db
        self._fastmail: Optional[FastMail] = None
    
    def _get_fastmail(self) -> FastMail:
        """Get or create FastMail instance with current configuration"""
        if self._fastmail is None:
            config_dict = EmailConfigService.get_email_config(self.db)
            
            connection_config = ConnectionConfig(
                MAIL_USERNAME=config_dict["mail_username"],
                MAIL_PASSWORD=config_dict["mail_password"],
                MAIL_FROM=config_dict["mail_from"],
                MAIL_PORT=config_dict["mail_port"],
                MAIL_SERVER=config_dict["mail_server"],
                MAIL_FROM_NAME=config_dict["mail_from_name"],
                MAIL_STARTTLS=config_dict["mail_starttls"],
                MAIL_SSL_TLS=config_dict["mail_ssl_tls"],
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True
            )
            self._fastmail = FastMail(connection_config)
        return self._fastmail
    
    def _reload_config(self):
        """Reload email configuration (useful after config changes)"""
        EmailConfigService.clear_cache()
        self._fastmail = None
    
    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_url: str
    ):
        """
        Send password reset email with reset link.
        
        Args:
            to_email: Recipient email address
            user_name: User's name
            reset_url: Password reset URL with token
        """
        config = EmailConfigService.get_email_config(self.db)
        subject = "Reimposta la tua password - Kinetic Brain"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #4A9EFF;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Reimposta la tua password</h1>
                <p>Ciao {user_name},</p>
                <p>Abbiamo ricevuto una richiesta per reimpostare la password del tuo account Kinetic Brain.</p>
                <p>Clicca sul pulsante qui sotto per reimpostare la password:</p>
                <a href="{reset_url}" class="button">Reimposta Password</a>
                <p>Oppure copia e incolla questo link nel tuo browser:</p>
                <p>{reset_url}</p>
                <p>Questo link scadrà tra 24 ore.</p>
                <p>Se non hai richiesto questa reimpostazione, ignora questa email. La tua password rimarrà invariata.</p>
                <div class="footer">
                    <p>Saluti,<br>Il team di Kinetic Brain</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        try:
            fastmail = self._get_fastmail()
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_body,
                subtype="html"
            )
            await fastmail.send_message(message)
            logger.info(f"Password reset email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            raise
    
    async def send_feedback_notification_email(
        self,
        feedback_type: str,
        subject: str,
        message: str,
        user_email: Optional[str] = None
    ):
        """
        Send feedback notification email to admin.
        
        Args:
            feedback_type: Type of feedback (bug, feature, improvement, question, other)
            subject: Feedback subject
            message: Feedback message
            user_email: Optional user email if feedback is from authenticated user
        """
        config = EmailConfigService.get_email_config(self.db)
        admin_email = config["admin_email"]
        
        if not admin_email:
            logger.warning("Admin email not configured, skipping feedback notification")
            return
        
        subject_email = f"[Feedback] {feedback_type}: {subject}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .info {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Nuovo Feedback Ricevuto</h1>
                <div class="info">
                    <p><strong>Tipo:</strong> {feedback_type}</p>
                    <p><strong>Oggetto:</strong> {subject}</p>
                    {f'<p><strong>Email Utente:</strong> {user_email}</p>' if user_email else '<p><strong>Email Utente:</strong> Anonimo</p>'}
                </div>
                <h2>Messaggio:</h2>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        
        try:
            fastmail = self._get_fastmail()
            message_obj = MessageSchema(
                subject=subject_email,
                recipients=[admin_email],
                body=html_body,
                subtype="html"
            )
            await fastmail.send_message(message_obj)
            logger.info(f"Feedback notification email sent to {admin_email}")
        except Exception as e:
            logger.error(f"Failed to send feedback notification email: {e}")
            raise
    
    async def send_notification_email(
        self,
        user_email: str,
        user_name: str,
        title: str,
        body: str,
        notification_type: str,
        data: Optional[dict] = None
    ):
        """
        Send notification email to user with custom title and body.
        
        Args:
            user_email: Recipient email address
            user_name: User's name
            title: Notification title
            body: Notification body/message
            notification_type: Type of notification (workout_reminder, new_workout, etc.)
            data: Optional additional data payload
        """
        config = EmailConfigService.get_email_config(self.db)
        subject = f"[Kinetic Brain] {title}"
        
        # Map notification types to Italian labels (optional, for better UX)
        type_labels = {
            "workout_reminder": "Promemoria Allenamento",
            "new_workout": "Nuovo Allenamento",
            "workout_completed": "Allenamento Completato",
            "plan_updates": "Aggiornamento Piano",
            "weekly_generation": "Generazione Settimana"
        }
        type_label = type_labels.get(notification_type, "Notifica")
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #4A9EFF 0%, #357ABD 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 30px 20px;
                }}
                .notification-type {{
                    display: inline-block;
                    background-color: #4A9EFF;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    margin-bottom: 20px;
                }}
                .title {{
                    font-size: 22px;
                    font-weight: 600;
                    color: #1a1a1a;
                    margin: 0 0 15px 0;
                }}
                .body {{
                    font-size: 16px;
                    color: #555;
                    margin: 0 0 30px 0;
                    white-space: pre-wrap;
                }}
                .footer {{
                    background-color: #f9f9f9;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                    border-top: 1px solid #e0e0e0;
                }}
                .footer p {{
                    margin: 5px 0;
                }}
                .footer a {{
                    color: #4A9EFF;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Kinetic Brain</h1>
                </div>
                <div class="content">
                    <span class="notification-type">{type_label}</span>
                    <h2 class="title">{title}</h2>
                    <div class="body">{body}</div>
                    <p style="color: #888; font-size: 14px; margin-top: 30px;">
                        Ciao {user_name},
                    </p>
                </div>
                <div class="footer">
                    <p>Saluti, il team di Kinetic Brain</p>
                    <p>
                        <a href="{config.get('frontend_url', 'http://localhost:8080')}">
                            Vai all'app
                        </a>
                    </p>
                    <p style="margin-top: 15px; font-size: 11px; color: #999;">
                        Puoi modificare le tue preferenze di notifica nelle impostazioni del profilo.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        try:
            fastmail = self._get_fastmail()
            message = MessageSchema(
                subject=subject,
                recipients=[user_email],
                body=html_body,
                subtype="html"
            )
            await fastmail.send_message(message)
            logger.info(f"Notification email sent to {user_email} - type: {notification_type}")
        except Exception as e:
            logger.error(f"Failed to send notification email to {user_email}: {e}")
            raise
