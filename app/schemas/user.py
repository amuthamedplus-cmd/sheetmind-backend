import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class UserTier(str, Enum):
    free = "free"
    pro = "pro"
    team = "team"


class UserBase(BaseModel):
    email: str
    name: str


class UserCreate(UserBase):
    google_id: str
    avatar_url: str | None = None


class UserResponse(UserBase):
    id: uuid.UUID
    tier: UserTier
    avatar_url: str | None
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    tier: UserTier | None = None
    payment_customer_id: str | None = None
    payment_subscription_id: str | None = None
