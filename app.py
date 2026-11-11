from flask import Flask

import config
import pages
import routes_convert  # The conversion API
import routes_quotes   # NEW: the quote API

app = Flask(__name__)
app.config["DB_FILE"] = config.DB_FILE

app.register_blueprint(pages.bp)
app.register_blueprint(routes_convert.bp)  # Switch on the conversion routes
app.register_blueprint(routes_quotes.bp)

if __name__ == "__main__":
    app.run(debug=True)