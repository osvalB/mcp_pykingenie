from fastmcp import FastMCP
import os
from pathlib import Path
import pykingenie

PY_KINETICS = pykingenie.KineticsAnalyzer()


def _resolve_desktop_dir() -> Path:
    """Return a Desktop directory path across Linux/macOS/Windows."""
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "desktop",
        home / "OneDrive" / "Desktop",  # common Windows redirected Desktop
    ]

    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / "Desktop")

    xdg_desktop = os.environ.get("XDG_DESKTOP_DIR")
    if xdg_desktop:
        candidates.append(Path(xdg_desktop).expanduser())

    for path in candidates:
        if path.is_dir():
            return path

    # If no desktop folder exists (e.g. headless systems), create a standard one under home.
    fallback = home / "Desktop"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# Define the path to the data directory on the user's Desktop.
current_dir = Path(__file__).resolve().parent
desktop_dir = _resolve_desktop_dir()
GLOBAL_USER_DATA_DIR = desktop_dir / "mcp_pykingenie" / "user_data"

# Keep example data path unchanged from original behavior.
EXAMPLE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_data")

# Create the global data directory if it doesn't exist.
GLOBAL_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Create a folder with the current date, inside data
from datetime import datetime
today = datetime.today().strftime('%Y-%m-%d')
DATA_DIR = GLOBAL_USER_DATA_DIR / today

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Location of the data files

# This is the shared MCP server instance
mcp = FastMCP("mcp_pykingenie")
