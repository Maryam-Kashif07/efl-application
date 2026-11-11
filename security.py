from flask import jsonify, redirect, request, session                   # Flask tools: JSON replies, redirects, the request and the login cookie

PUBLIC_ENDPOINTS = {"pages.index", "pages.login_page", "auth.register", "auth.login", "static"}  # The only routes anyone may open without logging in

def current_user_id():                                                  # The id of the person making this request
    """Return the signed-in user's id."""                               # Docstring
    return session["user_id"]                                           # Stored in the signed cookie when the user logs in

def require_login():                                                    # Runs before every request
    """Block every route that is not public unless the user is signed in."""  # Docstring
    if request.endpoint in PUBLIC_ENDPOINTS:                            # A public route
        return None                                                     # Let the request through
    if "user_id" in session:                                            # The user is signed in
        return None                                                     # Let the request through
    if request.path.startswith("/api/"):                                # An API call without a login
        return jsonify({"error": "Please sign in first."}), 401         # 401 means Unauthorised
    return redirect("/login")                                           # A page without a login: go to the login page

def add_security_headers(response):                                     # Runs after every request
    """Ask the browser to apply safe defaults."""                       # Docstring
    response.headers["X-Content-Type-Options"] = "nosniff"              # Stops the browser guessing file types
    response.headers["X-Frame-Options"] = "DENY"                        # Stops other sites showing our pages in a frame
    response.headers["Content-Security-Policy"] = "default-src 'self'"  # Only load scripts, styles and data from our own site
    response.headers["Cache-Control"] = "no-store"                      # Do not keep private pages in the browser cache
    return response                                                     # Send the response on