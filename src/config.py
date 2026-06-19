from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def get_db_path(lang: str = "fr") -> Path:
    return DATA_DIR / f"pokemon&cards_{lang}.db"
