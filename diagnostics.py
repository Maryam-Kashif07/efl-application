import json
from datetime import datetime
from pathlib import Path

import config
import database

BASE_DIR = Path(__file__).parent

def log_error_to_db(source, message, db_file=None):
    """Write the error to the error_log table. Return True if it worked."""
    try:
        database.log_error(source, message, db_file)
        return True
    except Exception as problem:
        log_to_file("Could not write to the error_log table: " + repr(problem) + " | original: " + message, "internal.log")
        return False

def log_to_file(message, filename="network.log"):
    """Append one timestamped line to a log file in the logs folder."""
    folder = BASE_DIR / config.LOG_DIR
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    with open(folder / filename, "a", encoding="utf-8") as log:
        log.write(stamp + " | " + message.replace("\n", " ") + "\n")

def cache_user_data(user_id, data):
    """Write the user's data to a JSON file in the cache folder. Return the path."""
    folder = BASE_DIR / config.CACHE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = folder / ("user_" + str(user_id) + "_" + stamp + ".json")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path