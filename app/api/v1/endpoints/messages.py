from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_telegram_service
from app.schemas.message import SendMessageRequest, SendMessageResponse
from app.services.telegram import TelegramError, TelegramService

router = APIRouter(tags=["messages"])


@router.post("/messages", response_model=SendMessageResponse)
async def send_message(
    payload: SendMessageRequest,
    telegram: TelegramService = Depends(get_telegram_service),
) -> SendMessageResponse:
    try:
        message_id = await telegram.send_message(payload.message)
    except TelegramError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return SendMessageResponse(message_id=message_id)
