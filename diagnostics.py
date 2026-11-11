import json                                                             # To write cached data as JSON
from datetime import datetime                                           # For timestamps
from pathlib import Path                                                # Folder and file handling

import config                                                           # Folder names
import database                                                         # The error_log table

BASE_DIR = Path(__file__).parent                                        # The project folder

def log_error_to_db(source, message, db_file=None):                     # Internal error: log the diagnostic data to the database
    """Write the error to the error_log table. Return True if it worked."""  # Docstring
    try:                                                                # The database itself may be the problem, so protect this call
        database.log_error(source, message, db_file)                    # Insert a row into error_log
        return True                                                     # It worked
    except Exception as problem:                                        # Writing to the database failed
        log_to_file("Could not write to the error_log table: " + repr(problem) + " | original: " + message, "internal.log")  # Fall back to a file so the evidence is not lost
        return False                                                    # Tell the caller it failed

def log_to_file(message, filename="network.log"):                       # Network failure: save the diagnostic data to the local file system
    """Append one timestamped line to a log file in the logs folder."""  # Docstring
    folder = BASE_DIR / config.LOG_DIR                                  # The logs folder
    folder.mkdir(parents=True, exist_ok=True)                           # Create it if it is missing
    stamp = datetime.now().isoformat(timespec="seconds")                # The time now, to the second
    with open(folder / filename, "a", encoding="utf-8") as log:         # "a" means add to the end of the file
        log.write(stamp + " | " + message.replace("\n", " ") + "\n")    # One line per event

def cache_user_data(user_id, data):                                     # System failure: keep the user's data immediately
    """Write the user's data to a JSON file in the cache folder. Return the path."""  # Docstring
    folder = BASE_DIR / config.CACHE_DIR                                # The cache folder
    folder.mkdir(parents=True, exist_ok=True)                           # Create it if it is missing
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")                 # A unique name part, down to microseconds
    path = folder / ("user_" + str(user_id) + "_" + stamp + ".json")    # The file name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")       # Save the data as readable JSON
    return path                                                         # Tell the caller where it went