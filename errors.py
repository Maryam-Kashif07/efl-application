"""Error types used across the application"""
class EFLError(Exception):
    """Base class for all EFL Errors"""
class InputError(EFLError):
    "The user typed something invalid. Show a clear message."""
class RateUnavailableError(EFLError):
    """No exchange rate could be loaded."""