from pydantic import BaseModel, Field, field_validator


class StationAccessUpdate(BaseModel):
    user_id: int
    station_ids: list[int] = Field(default_factory=list)

    @field_validator("station_ids")
    @classmethod
    def unique_station_ids(cls, value: list[int]) -> list[int]:
        return sorted(set(value))


class LineAccessUpdate(BaseModel):
    user_id: int
    line_ids: list[int] = Field(default_factory=list)

    @field_validator("line_ids")
    @classmethod
    def unique_line_ids(cls, value: list[int]) -> list[int]:
        return sorted(set(value))


class ReportingAccessUpdate(BaseModel):
    supervisor_user_id: int
    subordinate_user_ids: list[int] = Field(default_factory=list)
    relation_type: str = "REPORTING"

    @field_validator("subordinate_user_ids")
    @classmethod
    def unique_subordinate_ids(cls, value: list[int]) -> list[int]:
        return sorted(set(value))
