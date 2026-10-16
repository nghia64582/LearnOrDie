from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
WORKFLOWS_DIR = DATA_DIR / "workflows"
IMAGES_INDEX = IMAGES_DIR / "index.json"


def ensure_data_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
