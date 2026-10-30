from pydantic import BaseModel, Field
from typing import Optional, List, Any
import datetime

class BinBase(BaseModel):
    bin_id: str = Field(..., description="Unique alphanumeric bin ID, e.g. BIN-001")
    name: str = Field(..., description="Bin descriptive name, e.g. Main Gate")
    location: str = Field(..., description="Campus or area location")
    camera_url: str = Field(default="demo", description="IP Webcam HTTP/RTSP URL or 'demo'")
    camera_protocol: str = Field(default="http", description="http, rtsp, mjpeg, or demo")
    threshold: float = Field(default=85.0, ge=10.0, le=100.0)
    description: Optional[str] = ""
    active: bool = True
    floor_litter_enabled: bool = True

class BinCreate(BinBase):
    pass

class BinUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    camera_url: Optional[str] = None
    camera_protocol: Optional[str] = None
    threshold: Optional[float] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    floor_litter_enabled: Optional[bool] = None

class RoiUpdate(BaseModel):
    bin_roi: Optional[str] = None   # JSON serialized array of points [[x,y],...] or normalized bbox
    floor_roi: Optional[str] = None

class CameraTestRequest(BaseModel):
    camera_url: str
    camera_protocol: str = "http"

class CameraTestResponse(BaseModel):
    online: bool
    status: str
    message: str
    resolved_url: Optional[str] = None
    latency_ms: Optional[float] = None

class BinResponse(BinBase):
    id: int
    bin_roi: Optional[str] = ""
    floor_roi: Optional[str] = ""
    current_fill_percentage: float = 0.0
    current_status: str = "NORMAL"
    floor_litter_detected: bool = False
    camera_online: bool = False
    last_reading_time: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class ReadingResponse(BaseModel):
    id: int
    bin_id: int
    fill_percentage: float
    floor_litter_detected: bool
    waste_boxes_count: int
    timestamp: datetime.datetime

    class Config:
        from_attributes = True
