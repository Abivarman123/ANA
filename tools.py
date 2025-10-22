import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests
import serial
from langchain_community.tools import DuckDuckGoSearchRun
from livekit.agents import RunContext, function_tool


@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str,
) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}."


@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str,
) -> str:
    """
    Search the web using DuckDuckGo.
    """
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."


@function_tool()
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
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv(
            "GMAIL_APP_PASSWORD"
        )  # Use App Password, not regular password

        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Email sending failed: Gmail credentials not configured."

        # Create message
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject

        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg["Cc"] = cc_email
            recipients.append(cc_email)

        # Attach message body
        msg.attach(MIMEText(message, "plain"))

        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(gmail_user, gmail_password)

        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()

        logging.info(f"Email sent successfully to {to_email}")
        return f"Email sent successfully to {to_email}"

    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "Email sending failed: Authentication error. Please check your Gmail credentials."
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"An error occurred while sending email: {str(e)}"


# ============================================================================
# Arduino LED Controller
# ============================================================================

_serial_connection: Optional[serial.Serial] = None


def _get_connection() -> serial.Serial:
    """Get or create serial connection to Arduino."""
    global _serial_connection
    if _serial_connection is None or not _serial_connection.is_open:
        _serial_connection = serial.Serial("COM8", 9600, timeout=1)
        time.sleep(2)
    return _serial_connection


def _send_command(command: str) -> str:
    """Send command to Arduino."""
    try:
        conn = _get_connection()
        conn.write(f"{command}\n".encode())
        time.sleep(0.1)
        return conn.readline().decode().strip() if conn.in_waiting else "OK"
    except Exception as e:
        return f"Error: {e}"


@function_tool()
async def turn_led_on(
    context: RunContext,  # type: ignore
) -> str:
    """Turn ON the LED."""
    response = _send_command("12:ON")
    return (
        "✓ LED turned ON" if "OK" in response or "Error" not in response else response
    )


@function_tool()
async def turn_led_off(
    context: RunContext,  # type: ignore
) -> str:
    """Turn OFF the LED."""
    response = _send_command("12:OFF")
    return (
        "✓ LED turned OFF" if "OK" in response or "Error" not in response else response
    )


@function_tool()
async def turn_led_on_for_duration(
    context: RunContext,  # type: ignore
    seconds: int,
) -> str:
    """Turn ON the LED for specified seconds, then turn it OFF."""
    _send_command("12:ON")
    time.sleep(seconds)
    _send_command("12:OFF")
    return f"✓ LED was ON for {seconds} seconds"


@function_tool()
async def shutdown_agent(
    context: RunContext,  # type: ignore
) -> str:
    """Shut down the agent."""
    global _serial_connection

    if _serial_connection and _serial_connection.is_open:
        _send_command("12:OFF")
        _serial_connection.close()

    import asyncio
    import os

    async def delayed_shutdown():
        await asyncio.sleep(0.5)
        os._exit(0)

    asyncio.create_task(delayed_shutdown())
    return "✓ Shutting down. Goodbye, Sir."
