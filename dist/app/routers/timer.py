from fastapi import APIRouter
from ..state import sleep_timer
from ..models import TimerRequest

router = APIRouter()


@router.post("/api/timer/set")
async def set_timer(req: TimerRequest):
    sleep_timer.set_timer(req.minutes)
    return sleep_timer.get_status()


@router.post("/api/timer/stop")
async def stop_timer():
    sleep_timer.stop_timer()
    return sleep_timer.get_status()


@router.get("/api/timer/status")
async def get_timer_status():
    return sleep_timer.get_status()
