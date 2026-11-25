from decimal import Decimal

DB_FILE = "efl.db"
LOG_DIR = "logs"
CACHE_DIR = "cache"

MIN_TRANSACTION = Decimal("300")
MAX_TRANSACTION = Decimal("5000")
CURRENCIES = ["GBP", "USD", "EUR", "BRL", "JPY", "TRY"]

FEE_BANDS = [
    (Decimal("2500"), Decimal("1.5")),
    (Decimal("1500"), Decimal("2.0")),
    (Decimal("500"), Decimal("2.7")),
]
BASE_FEE_PERCENT = Decimal("3.5")

DEMO_USER_ID = 1

CURRENCY_NAMES = {
    "GBP": ("Pound sterling", "£"),
    "USD": ("US dollar", "$"),
    "EUR": ("Euro", "€"),
    "BRL": ("Brazilian real", "R$"),
    "JPY": ("Japanese yen", "¥"),
    "TRY": ("Turkish lira", "₺"),
}

SAMPLE_RATES_TO_USD = {
    "USD": "1.00",
    "GBP": "1.30",
    "EUR": "1.10",
    "BRL": "0.20",
    "JPY": "0.0067",
    "TRY": "0.030",
}

PLANS = [
    (1, "Basic Savings Plan", 20000, 50, None, 1.2, 2.4, 0.25),
    (2, "Savings Plan Plus", 30000, 50, 300, 3.0, 5.5, 0.3),
    (3, "Managed Stock Investments", None, 150, 1000, 4.0, 23.0, 1.3),
]

TAX_RULES = [
    (2, 12000, 10),
    (3, 12000, 10),
    (3, 40000, 20),
]

YEARS = (1, 5, 10)
MAX_QUOTE_INPUT = Decimal("10000000")

DEV_SECRET_KEY = "change-me-before-you-deploy"
PASSWORD_MIN_LENGTH = 8
USE_LIVE_RATES = False
RATE_URL = "https://open.er-api.com/v6/latest/USD"
RATE_TIMEOUT_SECONDS = 5
RATE_MAX_AGE_MINUTES = 10

import os

MAX_LOGIN_FAILURES = 5
LOGIN_LOCK_MINUTES = 5
SESSION_IDLE_MINUTES = 15
RESET_TOKEN_MINUTES = 30
SHOW_RESET_LINK = os.environ.get("EFL_SHOW_RESET_LINK", "1") == "1"
