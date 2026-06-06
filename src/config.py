from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
ARTISTS  = DATA_DIR / "artists.json"
ARCHIVE  = DATA_DIR / "archive.json"
