import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def resource_path(*paths):
    """Resolves resource paths for both bundled PyInstaller executable and development mode."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        candidate = os.path.join(os.path.abspath("."), *paths)
        if os.path.exists(candidate):
            return candidate
        base_path = _PROJECT_ROOT
    return os.path.join(base_path, *paths)

