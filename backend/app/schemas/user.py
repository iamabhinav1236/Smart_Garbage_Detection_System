from pydantic import BaseModel, Field
from typing import Optional
import datetime

class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: Optional[bool] = False

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
