from fastapi import APIRouter
import json
from ..config import settings_file
from ..models import AppSettings
from ..utils import safe_save_json

router = APIRouter()


@router.get("/api/settings")
async def get_settings():
    with open(settings_file, "r") as f:
        return json.load(f)


@router.post("/api/settings")
async def save_settings(settings: AppSettings):
    safe_save_json(settings_file, settings.model_dump())
    return {"status": "ok"}
