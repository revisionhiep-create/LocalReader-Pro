from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class LibraryItem(BaseModel):
    id: str
    fileName: str
    totalPages: int
    currentPage: int
    lastSentenceIndex: int
    lastAccessed: float


class ContentItem(BaseModel):
    id: str
    pages: List[str]


class PronunciationRule(BaseModel):
    id: str
    original: str
    replacement: str
    match_case: bool
    word_boundary: bool
    is_regex: Optional[bool] = False


class AppSettings(BaseModel):
    pronunciationRules: List[PronunciationRule]
    ignoreList: List[str]
    voice_id: Optional[str] = "af_bella"
    speed: Optional[float] = 1.0
    font_size: Optional[int] = 16
    header_footer_mode: Optional[str] = "off"
    engine_mode: Optional[str] = "gpu"
    ui_language: Optional[str] = "en"
    pause_settings: Optional[Dict[str, int]] = {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 800,
    }


class TimerRequest(BaseModel):
    minutes: int


class ExportRequest(BaseModel):
    doc_id: str
    voice: str = "af_bella"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []


class SynthesisRequest(BaseModel):
    text: str
    voice: str = "af_sky"
    speed: float = 1.0
    rules: List[PronunciationRule]
    ignore_list: List[str] = []
    pause_settings: Optional[Dict[str, int]] = {
        "comma": 300,
        "period": 600,
        "question": 600,
        "exclamation": 600,
        "colon": 400,
        "semicolon": 400,
        "newline": 800,
    }
