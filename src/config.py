from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "olist.sqlite" / "olist.sqlite"
DEMO_DB_PATH = PROJECT_ROOT / "demo_data" / "olist_demo.sqlite"
DEFAULT_SCHEMA_DIR = PROJECT_ROOT / "schemas"
DEFAULT_SCHEMA_PATH = DEFAULT_SCHEMA_DIR / "olist_schema.json"
DEFAULT_MODEL = "gpt-4o"
DEFAULT_MAX_RESULT_ROWS = 50


def get_bundled_db_path() -> Path | None:
    if DEFAULT_DB_PATH.exists():
        return DEFAULT_DB_PATH
    if DEMO_DB_PATH.exists():
        return DEMO_DB_PATH
    return None
