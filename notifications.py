# -*- coding: utf-8 -*-
"""
notifications.py — Stub for outbound notifications
====================================================
Placeholder for integrating chat / email alerts after
user provisioning actions.

Supported channels (to implement):
  - Email        (smtplib / SendGrid / SES)
  - Webex Teams  (POST to https://webexapis.com/v1/messages)
  - Slack        (POST to Slack Incoming Webhook URL)

Usage in app.py:
    from notifications import send_notification
    send_notification(
        channel="webex",
        message=f"User {username} created on {dbname} ({env})",
    )
"""

import logging

logger = logging.getLogger(__name__)


def send_notification(channel: str = "log", message: str = "",
                      recipient: str = None, **kwargs):
    """
    Send a notification via the specified channel.

    Parameters
    ----------
    channel   : 'email' | 'webex' | 'slack' | 'log'  (default: 'log')
    message   : body text to send
    recipient : email address, Webex room ID, or Slack channel name
    **kwargs  : any extra channel-specific options
    """
    if channel == "log":
        logger.info("[NOTIFICATION] %s", message)

    elif channel == "email":
        # ── TODO: wire up smtplib or SendGrid ──────────────────────────
        # import smtplib
        # from email.message import EmailMessage
        # msg = EmailMessage()
        # msg["Subject"] = "PG User API — Action Completed"
        # msg["From"]    = "pg-api@example.com"
        # msg["To"]      = recipient
        # msg.set_content(message)
        # with smtplib.SMTP("smtp.example.com", 587) as s:
        #     s.starttls()
        #     s.login("user", "pass")
        #     s.send_message(msg)
        logger.info("[EMAIL stub] To: %s | %s", recipient, message)

    elif channel == "webex":
        # ── TODO: wire up Webex Teams ──────────────────────────────────
        # import requests
        # WEBEX_TOKEN = "Bearer YOUR_TOKEN_HERE"
        # WEBEX_ROOM  = recipient  # Webex roomId
        # requests.post(
        #     "https://webexapis.com/v1/messages",
        #     headers={"Authorization": WEBEX_TOKEN,
        #              "Content-Type": "application/json"},
        #     json={"roomId": WEBEX_ROOM, "text": message},
        # )
        logger.info("[WEBEX stub] Room: %s | %s", recipient, message)

    elif channel == "slack":
        # ── TODO: wire up Slack Incoming Webhook ──────────────────────
        # import requests
        # SLACK_WEBHOOK = "https://hooks.slack.com/services/T.../B.../..."
        # requests.post(SLACK_WEBHOOK, json={"text": message})
        logger.info("[SLACK stub] Channel: %s | %s", recipient, message)

    else:
        logger.warning("Unknown notification channel: %s", channel)
