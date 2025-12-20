"""Email-related tools."""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from livekit.agents import RunContext, function_tool

from ..config import config
from .base import handle_tool_error


@function_tool()
@handle_tool_error("send_email")
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None,
) -> str:
    """
    Send an email through Gmail.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    if not config.is_email_configured():
        logging.error("Gmail credentials not found in environment variables")
        return "Email sending failed: Gmail credentials not configured."

    email_config = config.email

    # Create message
    msg = MIMEMultipart()
    msg["From"] = email_config["user"]
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add CC if provided
    recipients = [to_email]
    if cc_email:
        msg["Cc"] = cc_email
        recipients.append(cc_email)

    # Attach message body
    msg.attach(MIMEText(message, "plain"))

    def _send_email_blocking():
        """Blocking email send operation to run in executor."""
        try:
            # Connect to Gmail SMTP server
            server = smtplib.SMTP(
                email_config["smtp_server"], email_config["smtp_port"]
            )
            server.starttls()
            server.login(email_config["user"], email_config["password"])

            # Send email
            text = msg.as_string()
            server.sendmail(email_config["user"], recipients, text)
            server.quit()

            logging.info(f"Email sent successfully to {to_email}")
            return f"Email sent successfully to {to_email}"

        except smtplib.SMTPAuthenticationError:
            logging.error("Gmail authentication failed")
            return "Email sending failed: Authentication error. Please check your Gmail credentials."
        except smtplib.SMTPException as e:
            logging.error(f"SMTP error occurred: {e}")
            return f"Email sending failed: SMTP error - {str(e)}"

    # Run blocking SMTP operations in executor
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_email_blocking)
