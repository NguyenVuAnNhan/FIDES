import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["demo"])

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_dataset.json"
SYNTHETIC_DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_demo_dataset.json"


@router.get("/dataset")
def get_demo_dataset() -> dict[str, Any]:
    return _load_json(DATASET_PATH)


@router.get("/synthetic-dataset")
def get_synthetic_demo_dataset() -> dict[str, Any]:
    return _load_json(SYNTHETIC_DATASET_PATH)


@lru_cache
def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
