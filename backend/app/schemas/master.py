from datetime import date
from pydantic import BaseModel, Field


class ActiveMixin(BaseModel):
    is_active: bool = True


class LineCreate(BaseModel):
    line_code: str = Field(..., min_length=1, max_length=50)
    line_name: str = Field(..., min_length=1, max_length=100)


class LineUpdate(BaseModel):
    line_code: str | None = Field(default=None, min_length=1, max_length=50)
    line_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class LineOut(LineCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class ContractorCreate(BaseModel):
    contractor_code: str = Field(..., min_length=1, max_length=50)
    contractor_name: str = Field(..., min_length=1, max_length=200)
    contact_person: str | None = None
    mobile: str | None = None
    email: str | None = None


class ContractorUpdate(BaseModel):
    contractor_code: str | None = Field(default=None, min_length=1, max_length=50)
    contractor_name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_person: str | None = None
    mobile: str | None = None
    email: str | None = None
    is_active: bool | None = None


class ContractorOut(ContractorCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class StationCreate(BaseModel):
    station_code: str = Field(..., min_length=1, max_length=50)
    station_name: str = Field(..., min_length=1, max_length=150)
    line_id: int
    latitude: float | None = None
    longitude: float | None = None


class StationUpdate(BaseModel):
    station_code: str | None = Field(default=None, min_length=1, max_length=50)
    station_name: str | None = Field(default=None, min_length=1, max_length=150)
    line_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


class StationOut(StationCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class ContractCreate(BaseModel):
    contract_code: str = Field(..., min_length=1, max_length=80)
    tender_no: str | None = None
    contract_name: str = Field(..., min_length=1, max_length=250)
    contractor_id: int
    start_date: date
    end_date: date
    extension_end_date: date | None = None
    monthly_bill_value_default: float = 0
    grading_scheme_id: int
    kpi6_threshold_percent: float = 90
    kpi6_penalty_percent: float = 5


class ContractUpdate(BaseModel):
    contract_code: str | None = Field(default=None, min_length=1, max_length=80)
    tender_no: str | None = None
    contract_name: str | None = Field(default=None, min_length=1, max_length=250)
    contractor_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    extension_end_date: date | None = None
    monthly_bill_value_default: float | None = None
    grading_scheme_id: int | None = None
    kpi6_threshold_percent: float | None = None
    kpi6_penalty_percent: float | None = None
    is_active: bool | None = None


class ContractOut(ContractCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class ContractStationCreate(BaseModel):
    station_id: int


class ContractStationOut(BaseModel):
    id: int
    contract_id: int
    station_id: int
    is_active: bool
    model_config = {"from_attributes": True}


class InspectionAttributeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=250)
    description: str | None = None
    sort_order: int = 1


class InspectionAttributeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class InspectionAttributeOut(InspectionAttributeCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class InspectionSubAreaCreate(BaseModel):
    attribute_id: int
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=250)
    photo_min_required: int = Field(1, ge=0, le=3)
    photo_max_allowed: int = Field(3, ge=0, le=10)
    video_required: bool = False
    video_max_seconds: int = Field(15, ge=1, le=300)
    allow_na: bool = True
    sort_order: int = 1


class InspectionSubAreaUpdate(BaseModel):
    attribute_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=250)
    photo_min_required: int | None = Field(default=None, ge=0, le=3)
    photo_max_allowed: int | None = Field(default=None, ge=0, le=10)
    video_required: bool | None = None
    video_max_seconds: int | None = Field(default=None, ge=1, le=300)
    allow_na: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class InspectionSubAreaOut(InspectionSubAreaCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class GradingSchemeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)


class GradingSchemeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None


class GradingSchemeOut(GradingSchemeCreate, ActiveMixin):
    id: int
    model_config = {"from_attributes": True}


class GradingOptionCreate(BaseModel):
    scheme_id: int
    grade_code: str = Field(..., min_length=1, max_length=5)
    label: str = Field(..., min_length=1, max_length=100)
    percentage: float = Field(..., ge=0, le=100)
    sort_order: int = 1


class GradingOptionUpdate(BaseModel):
    scheme_id: int | None = None
    grade_code: str | None = Field(default=None, min_length=1, max_length=5)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    percentage: float | None = Field(default=None, ge=0, le=100)
    sort_order: int | None = None


class GradingOptionOut(GradingOptionCreate):
    id: int
    model_config = {"from_attributes": True}
