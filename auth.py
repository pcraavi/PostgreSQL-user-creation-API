# -*- coding: utf-8 -*-
"""
auth.py — HTTP Basic Authentication helper
==========================================
Provides a simple constant-time comparison for Basic Auth credentials.

For production, replace with a token-based or OAuth2 flow.
"""

import hmac


def check_basic_auth(provided_user: str, provided_pass: str,
                     expected_user: str, expected_pass: str) -> bool:
    """
    Validate Basic Auth credentials using constant-time comparison
    to prevent timing-based enumeration attacks.

    Returns True if both username and password match, False otherwise.
    """
    user_ok = hmac.compare_digest(provided_user or "", expected_user)
    pass_ok = hmac.compare_digest(provided_pass or "", expected_pass)
    return user_ok and pass_ok
