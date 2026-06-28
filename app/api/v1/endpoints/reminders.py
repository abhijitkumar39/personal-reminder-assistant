from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.reminder import (
    ReminderCreate,
    ReminderResponse,
    ReminderStatus,
    ReminderUpdate,
)
from app.services.reminder import (
    ReminderNotFoundError,
    ReminderNotPendingError,
    cancel_reminder,
    create_reminder,
    get_reminder,
    list_reminders,
    update_reminder,
)

router = APIRouter(tags=["reminders"])


@router.post("/reminders", response_model=ReminderResponse, status_code=201)
def create_reminder_endpoint(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
) -> ReminderResponse:
    reminder = create_reminder(db, payload)
    return ReminderResponse.model_validate(reminder)


@router.get("/reminders", response_model=list[ReminderResponse])
def list_reminders_endpoint(
    status: ReminderStatus | None = Query(default=ReminderStatus.PENDING),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    reminders = list_reminders(db, status=status)
    return [ReminderResponse.model_validate(reminder) for reminder in reminders]


@router.get("/reminders/{reminder_id}", response_model=ReminderResponse)
def get_reminder_endpoint(
    reminder_id: int,
    db: Session = Depends(get_db),
) -> ReminderResponse:
    try:
        reminder = get_reminder(db, reminder_id)
    except ReminderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Reminder not found") from exc

    return ReminderResponse.model_validate(reminder)


@router.patch("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder_endpoint(
    reminder_id: int,
    payload: ReminderUpdate,
    db: Session = Depends(get_db),
) -> ReminderResponse:
    try:
        reminder = update_reminder(db, reminder_id, payload)
    except ReminderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Reminder not found") from exc
    except ReminderNotPendingError as exc:
        raise HTTPException(
            status_code=409,
            detail="Only pending reminders can be updated",
        ) from exc

    return ReminderResponse.model_validate(reminder)


@router.delete("/reminders/{reminder_id}", response_model=ReminderResponse)
def cancel_reminder_endpoint(
    reminder_id: int,
    db: Session = Depends(get_db),
) -> ReminderResponse:
    try:
        reminder = cancel_reminder(db, reminder_id)
    except ReminderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Reminder not found") from exc
    except ReminderNotPendingError as exc:
        raise HTTPException(
            status_code=409,
            detail="Only pending reminders can be cancelled",
        ) from exc

    return ReminderResponse.model_validate(reminder)
