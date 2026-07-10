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
    # Start Inspection remains station-driven. kpi_category lets the same inspection
    # workflow launch KPI-6 cleanliness or another KPI form such as chemicals.
    station_id: int
    kpi_category: str = "KPI_6_CLEANLINESS"
    contract_id: int | None = None
    inspection_type: InspectionType | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy: float | None = None
    device_info: dict | None = None
    remarks: str | None = None


class InspectionDraftIn(BaseModel):
    """Legacy checklist payload retained for backward compatibility.

    The new mobile-friendly UI uses InspectionEntryCreate instead.
    """
    attribute_scores: list[AttributeScoreIn] = Field(default_factory=list)
    observations: list[ObservationIn] = Field(default_factory=list)
    remarks: str | None = None


class InspectionSubmitIn(InspectionDraftIn):
    pass


class InspectionEntryCreate(BaseModel):
    attribute_id: int
    sub_area_id: int
    grade_code: str
    remarks: str | None = None
    captured_latitude: float | None = None
    captured_longitude: float | None = None
    gps_accuracy: float | None = None
    captured_at: datetime | None = None


class InspectionEntryUpdate(BaseModel):
    grade_code: str | None = None
    remarks: str | None = None
    captured_latitude: float | None = None
    captured_longitude: float | None = None
    gps_accuracy: float | None = None
    captured_at: datetime | None = None


class InspectionEntrySubmitIn(BaseModel):
    remarks: str | None = None


class InspectionOut(BaseModel):
    id: int
    inspection_no: str
    contract_id: int
    station_id: int
    inspection_type: InspectionType
    kpi_category: str = "KPI_6_CLEANLINESS"
    inspection_date: date
    submitted_by: int
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy: float | None = None
    status: InspectionStatus
    remarks: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None
    model_config = {"from_attributes": True}


class MediaOut(BaseModel):
    id: int
    inspection_id: int
    inspection_entry_id: int | None = None
    attribute_id: int
    sub_area_id: int
    media_type: MediaType
    object_path: str
    original_file_name: str
    mime_type: str | None = None
    file_size: int | None = None
    checksum: str | None = None
    captured_latitude: float | None = None
    captured_longitude: float | None = None
    gps_accuracy: float | None = None
    captured_at: datetime | None = None
    model_config = {"from_attributes": True}


class EntryMediaPreviewOut(BaseModel):
    id: int
    inspection_id: int
    inspection_entry_id: int | None = None
    media_type: MediaType
    original_file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    captured_latitude: float | None = None
    captured_longitude: float | None = None
    gps_accuracy: float | None = None
    captured_at: datetime | None = None
    preview_url: str


class InspectionEntryOut(BaseModel):
    id: int
    inspection_id: int
    entry_no: str
    attribute_id: int
    sub_area_id: int
    grade_code: str
    grade_percentage: float
    remarks: str | None = None
    captured_latitude: float | None = None
    captured_longitude: float | None = None
    gps_accuracy: float | None = None
    captured_at: datetime | None = None
    created_by: int
    photo_count: int = 0
    video_count: int = 0
    media_files: list[EntryMediaPreviewOut] = Field(default_factory=list)
    attribute_name: str | None = None
    sub_area_name: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
