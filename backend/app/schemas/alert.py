from pydantic import BaseModel
from typing import Optional
import datetime

class AlertResponse(BaseModel):
    id: int
    bin_id: int
    bin_code: str
    location: str
    fill_percentage: float
    threshold: float
    recipient: str
    sent_at: datetime.datetime
    status: str
    snapshot_path: Optional[str] = None
    message: Optional[str] = ""

    class Config:
        from_attributes = True
