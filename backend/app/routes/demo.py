import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["demo"])

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_dataset.json"


@router.get("/dataset")
def get_demo_dataset() -> dict[str, Any]:
    return _load_demo_dataset()


@lru_cache
def _load_demo_dataset() -> dict[str, Any]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))

