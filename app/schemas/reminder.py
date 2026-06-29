from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from app.services.recurrence import RecurrenceInterval
from app.utils.datetime import to_utc, utc_now


class ReminderStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"


def _must_be_future(value: datetime) -> datetime:
    remind_at = to_utc(value)
    if remind_at <= utc_now():
        raise ValueError("must be in the future")
    return remind_at


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str | None = Field(None, max_length=4096)
    remind_at: datetime
    recurrence: RecurrenceInterval = RecurrenceInterval.NONE
    recurrence_end_at: datetime | None = None

    @field_validator("remind_at")
    @classmethod
    def remind_at_must_be_future(cls, value: datetime) -> datetime:
        return _must_be_future(value)

    @field_validator("recurrence_end_at")
    @classmethod
    def recurrence_end_at_must_be_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return _must_be_future(value)

    @model_validator(mode="after")
    def recurrence_end_after_first(self) -> "ReminderCreate":
        if self.recurrence == RecurrenceInterval.NONE:
            if self.recurrence_end_at is not None:
                raise ValueError("recurrence_end_at is only valid for recurring reminders")
            return self

        if self.recurrence_end_at is not None:
            end_at = to_utc(self.recurrence_end_at)
            remind_at = to_utc(self.remind_at)
            if end_at <= remind_at:
                raise ValueError("recurrence_end_at must be after remind_at")

        return self


class ReminderUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    message: str | None = Field(None, max_length=4096)
    remind_at: datetime | None = None
    recurrence: RecurrenceInterval | None = None
    recurrence_end_at: datetime | None = None

    @field_validator("remind_at", "recurrence_end_at")
    @classmethod
    def datetime_fields_must_be_future(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return value
        return _must_be_future(value)


class ReminderResponse(BaseModel):
    id: int
    title: str
    message: str | None
    remind_at: datetime
    recurrence: RecurrenceInterval
    recurrence_end_at: datetime | None
    status: ReminderStatus
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}

    @field_serializer("remind_at", "recurrence_end_at", "created_at", "sent_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return to_utc(value).isoformat().replace("+00:00", "Z")
