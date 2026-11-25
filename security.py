import time
from urllib.parse import quote

from flask import jsonify, redirect, request, session

import config

PUBLIC_ENDPOINTS = {
    "pages.index",
    "pages.login_page",
    "pages.register_page",
    "pages.forgot_password_page",
    "pages.reset_password_page",
    "auth.register",
    "auth.login",
    "auth.forgot_password",
    "auth.reset_password",
    "static",
}

INACTIVE_MESSAGE = "You were signed out because you were inactive. Please log in again."


def current_user_id():
    return session["user_id"]


def signed_out_for_inactivity():
    if "user_id" not in session:
        return False
    now = time.time()
    last_seen = session.get("last_seen")
    session["last_seen"] = now
    if last_seen is not None and now - last_seen > config.SESSION_IDLE_MINUTES * 60:
        session.clear()
        return True
    return False


def require_login():
    if request.endpoint is None or request.endpoint == "static":
        return None
    expired = signed_out_for_inactivity()
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if "user_id" in session:
        return None
    if request.path.startswith("/api/"):
        if expired:
            return jsonify({"error": INACTIVE_MESSAGE, "expired": True}), 401
        return jsonify({"error": "Please sign in first."}), 401
    if expired:
        return redirect("/login?expired=1&next=" + quote(request.path))
    return redirect("/login?next=" + quote(request.path))


def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com"
    response.headers["Cache-Control"] = "no-store"
    return response
