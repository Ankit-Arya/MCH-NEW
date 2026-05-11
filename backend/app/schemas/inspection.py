from datetime import date, datetime
from pydantic import BaseModel, Field
from app.models.all_models import InspectionType, InspectionStatus, MediaType


class AttributeScoreIn(BaseModel):
    attribute_id: int
    grade_code: str
    remarks: str | None = None


class ObservationIn(BaseModel):
    attribute_id: int
    sub_area_id: int
    is_applicable: bool = True
    na_reason: str | None = None
    observation_text: str | None = None


class InspectionStartIn(BaseModel):
    contract_id: int
    station_id: int
    inspection_type: InspectionType
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy: float | None = None
    device_info: dict | None = None
    remarks: str | None = None


class InspectionDraftIn(BaseModel):
    attribute_scores: list[AttributeScoreIn] = Field(default_factory=list)
    observations: list[ObservationIn] = Field(default_factory=list)
    remarks: str | None = None


class InspectionSubmitIn(InspectionDraftIn):
    pass


class InspectionOut(BaseModel):
    id: int
    inspection_no: str
    contract_id: int
    station_id: int
    inspection_type: InspectionType
    inspection_date: date
    submitted_by: int
    latitude: float | None = None
    longitude: float | None = None
    status: InspectionStatus
    remarks: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class MediaOut(BaseModel):
    id: int
    inspection_id: int
    attribute_id: int
    sub_area_id: int
    media_type: MediaType
    object_path: str
    original_file_name: str
    mime_type: str | None = None
    file_size: int | None = None
    checksum: str | None = None
    model_config = {"from_attributes": True}
