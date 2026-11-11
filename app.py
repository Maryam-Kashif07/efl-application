"""EFL application: creates the Flask app, registers the routes and handles failures."""  # Docstring: what this file does
import os                                                               # To read the secret key from the environment
import traceback                                                        # To capture the full error text for the log

from flask import Flask, jsonify, render_template, request, session     # Flask tools
from werkzeug.exceptions import HTTPException                           # The kind of error Flask raises for 404, 405 and so on

import config                                                           # Settings
import database                                                         # Saving a draft when something fails
import diagnostics                                                      # The failure behaviours
import pages                                                            # The HTML pages
import routes_auth                                                      # Register, login and logout
import routes_convert                                                   # The conversion API
import routes_history                                                   # History and drafts
import routes_quotes                                                    # The quote API
import security                                                         # Login checks and headers

app = Flask(__name__)                                                   # Create the web application
app.config["DB_FILE"] = config.DB_FILE                                  # Which database file the routes use; tests change this
app.secret_key = os.environ.get("EFL_SECRET_KEY", config.DEV_SECRET_KEY)  # The key that signs the login cookie; real sites keep it secret
app.config["SESSION_COOKIE_HTTPONLY"] = True                            # JavaScript cannot read the login cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"                           # The cookie is not sent with requests started by other sites

app.register_blueprint(pages.bp)                                        # Switch on the page routes
app.register_blueprint(routes_auth.bp)                                  # Switch on register, login and logout
app.register_blueprint(routes_convert.bp)                               # Switch on the conversion routes
app.register_blueprint(routes_quotes.bp)                                # Switch on the quote routes
app.register_blueprint(routes_history.bp)                               # Switch on history and drafts

app.before_request(security.require_login)                              # Check the login before every request: everything is private unless listed as public
app.after_request(security.add_security_headers)                        # Add the safe headers to every response

@app.errorhandler(Exception)                                            # Catches every error nobody else handled
def handle_internal_error(error):                                       # Runs instead of showing a crash page
    if isinstance(error, HTTPException):                                # Expected errors such as 404 Not Found
        if request.path.startswith("/api/"):                            # An API call
            return jsonify({"error": error.description}), error.code    # JSON with the right code
        return render_template("error.html", message=error.description), error.code  # A friendly page
    db_file = app.config["DB_FILE"]                                     # Which database to log to
    diagnostics.log_error_to_db(request.path, traceback.format_exc(), db_file)  # Internal error: log all diagnostic data to the database
    user_id = session.get("user_id")                                    # Who was using the app, if anyone
    saved_note = ""                                                     # Text about saved data
    draft_id = None                                                     # The draft id, if we manage to save one
    data = request.get_json(silent=True) or request.form.to_dict()      # The data the user had just sent
    if data:                                                            # There is something to keep
        diagnostics.cache_user_data(user_id, data)                      # System failure: cache the user's data immediately in the cache folder
        saved_note = " Your entries have been saved."                   # Tell the user their work is safe
        if user_id is not None:                                         # Drafts belong to a user
            try:                                                        # The database may be what failed
                draft_id = database.save_draft(user_id, data, db_file)  # Also keep a draft row in the database
            except Exception:                                           # The database is not working
                draft_id = None                                         # The file cache still holds the data
    message = "Something went wrong on our side." + saved_note + " Please try again."  # Friendly text with no technical details
    if request.path.startswith("/api/"):                                # An API call
        return jsonify({"error": message, "draft_id": draft_id}), 500   # 500 means Internal Server Error
    return render_template("error.html", message=message), 500          # A friendly page

if __name__ == "__main__":                                              # True only when you run python app.py directly
    app.run(debug=True)