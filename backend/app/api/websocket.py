from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import subscribe, get_history

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    for event in get_history(job_id):
        await websocket.send_json(event)
    try:
        async for event in subscribe(job_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
