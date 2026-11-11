from werkzeug.security import check_password_hash, generate_password_hash  # Flask's own hashing tools; installed with Flask

def hash_password(password):                                            # Turn a password into a hash for storing
    """Return a salted hash of the password."""                         # Docstring
    return generate_password_hash(password)                             # A random salt is added, so the same password gives a different hash each time

def check_password(password, password_hash):                            # Compare a typed password with the stored hash
    """Return True if the password matches the stored hash."""          # Docstring
    return check_password_hash(password_hash, password)                 # The hash cannot be reversed; this hashes the typed password the same way and compares