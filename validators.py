import re                                      # NEW: regular expressions, for email and phone patterns
from decimal import Decimal, InvalidOperation                        

import config                  # The limits and currency codes live in config.py
import quotes                  # NEW: the quote engine, for the plan rules
from errors import InputError  # The error type for bad user input                                           

def validate_amount(text):                                              
    """Return the amount as a Decimal, or raise InputError with a clear message."""  
    try:                                                                
        amount = Decimal(str(text).strip())                             
    except InvalidOperation:                                            
        raise InputError("Enter the amount as a number, for example 500.")  
    if not amount.is_finite():                                          
        raise InputError("Enter the amount as a number, for example 500.")  
    if amount.as_tuple().exponent < -2:                                 
        raise InputError("Use at most two decimal places.")             
    if amount < config.MIN_TRANSACTION or amount > config.MAX_TRANSACTION:  
        raise InputError(f"The amount must be between {config.MIN_TRANSACTION:,} and {config.MAX_TRANSACTION:,}.")  
    return amount                                                       

def validate_currency(code):                                            
    """Return the code in capitals, or raise InputError."""             
    clean = str(code).strip().upper()                                   
    if clean not in config.CURRENCIES:                                  
        raise InputError("Choose one of: " + ", ".join(config.CURRENCIES) + ".")  
    return clean                                                        

def validate_money(text, label):                                        # Check a money amount typed on the quote page
    """Return a Decimal that is not negative and has at most two decimal places."""  # Docstring
    try:                                                                # Try to turn the text into a number
        value = Decimal(str(text).strip())                              # str() copes with numbers and None
    except InvalidOperation:                                            # Not a number
        raise InputError(f"Enter the {label} as a number, for example 250.00.")  # A message the user can act on
    if not value.is_finite():                                           # Block NaN and Infinity
        raise InputError(f"Enter the {label} as a number, for example 250.00.")  # Same message
    if value.as_tuple().exponent < -2:                                  # More than two decimal places
        raise InputError(f"Use at most two decimal places for the {label}.")  # Tell the user what to fix
    if value < 0:                                                       # Negative
        raise InputError(f"The {label} cannot be negative.")            # Tell the user
    if value > config.MAX_QUOTE_INPUT:                                  # Absurdly large
        raise InputError(f"The {label} is too large.")                  # Tell the user
    return value                                                        # The clean Decimal

def validate_plan_id(value, plans):                                     # Check the chosen investment type
    """Return the chosen plan dictionary, or raise InputError."""       # Docstring
    try:                                                                # Try to read a whole number
        plan_id = int(str(value).strip())                               # The browser sends the id as text
    except ValueError:                                                  # Not a whole number
        raise InputError("Choose an investment type.")                  # Tell the user
    for plan in plans:                                                  # Look for it
        if plan["plan_id"] == plan_id:                                  # Found
            return plan                                                 # Return the plan
    raise InputError("Choose an investment type.")                      # No plan has that id

def validate_quote_inputs(plan, lump_sum, monthly):                     # Does the user meet the chosen plan's rules?
    """Raise InputError listing every rule the chosen plan breaks."""   # Docstring
    reasons = quotes.check_eligibility(plan, lump_sum, monthly)         # Ask the quote engine
    if reasons:                                                         # At least one rule is broken
        raise InputError(" ".join(reasons))                             # Join the messages into one

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")               # NEW: something@something.something with no spaces
PHONE_PATTERN = re.compile(r"^\+?[0-9 ()-]{7,20}$")                     # NEW: digits, spaces, brackets and dashes; an optional leading +

def validate_registration(data):                                        # NEW: check the create-account form
    """Return clean name, email, phone and password, or raise InputError."""  # Docstring
    name = str(data.get("name") or "").strip()                          # Name, with spaces removed
    email = str(data.get("email") or "").strip().lower()                # Email in lower case, so Sam@x.com and sam@x.com match
    phone = str(data.get("phone") or "").strip()                        # Phone is optional
    password = str(data.get("password") or "")                          # Never strip a password: spaces may be part of it
    if not 1 <= len(name) <= 100:                                       # Name must be present and not huge
        raise InputError("Enter your name (up to 100 characters).")     # Tell the user
    if not EMAIL_PATTERN.match(email) or len(email) > 254:              # Email must look like an email
        raise InputError("Enter a valid email address.")                # Tell the user
    if phone and not PHONE_PATTERN.match(phone):                        # If a phone number was given it must look right
        raise InputError("Enter a valid phone number, or leave it empty.")  # Tell the user
    if len(password) < config.PASSWORD_MIN_LENGTH or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):  # Long enough, with a letter and a digit
        raise InputError(f"The password needs at least {config.PASSWORD_MIN_LENGTH} characters, including a letter and a number.")  # Tell the user the rule
    return {"name": name, "email": email, "phone": phone or None, "password": password}  # The clean values