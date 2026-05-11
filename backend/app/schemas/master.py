from datetime import date
from pydantic import BaseModel


class LineOut(BaseModel):
    id: int
    line_code: str
    line_name: str
    model_config = {"from_attributes": True}


class StationCreate(BaseModel):
    station_code: str
    station_name: str
    line_id: int
    latitude: float | None = None
    longitude: float | None = None


class StationOut(StationCreate):
    id: int
    model_config = {"from_attributes": True}


class ContractCreate(BaseModel):
    contract_code: str
    tender_no: str | None = None
    contract_name: str
    contractor_id: int
    start_date: date
    end_date: date
    extension_end_date: date | None = None
    monthly_bill_value_default: float = 0
    grading_scheme_id: int


class ContractOut(ContractCreate):
    id: int
    model_config = {"from_attributes": True}
