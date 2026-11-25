from werkzeug.security import check_password_hash, generate_password_hash

def hash_password(password):
    """Return a salted hash of the password."""
    return generate_password_hash(password)

def check_password(password, password_hash):
    """Return True if the password matches the stored hash."""
    return check_password_hash(password_hash, password)