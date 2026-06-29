from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


KPI_6_CLEANLINESS = "KPI_6_CLEANLINESS"
KPI_CHEMICALS = "KPI_CHEMICALS"


class ChemicalTimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class InspectionKpiContext(Base, ChemicalTimestampMixin):
    __tablename__ = "inspection_kpi_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False, unique=True, index=True)
    kpi_category: Mapped[str] = mapped_column(String(60), nullable=False, default=KPI_6_CLEANLINESS, index=True)


class KpiChemical(Base, ChemicalTimestampMixin):
    __tablename__ = "kpi_chemicals"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="Ltr/Kg/No")
    default_required_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    station_requirements: Mapped[list["StationChemicalRequirement"]] = relationship(back_populates="chemical")


class StationChemicalRequirement(Base, ChemicalTimestampMixin):
    __tablename__ = "station_chemical_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False, index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("kpi_chemicals.id"), nullable=False)
    required_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(40))
    remarks: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    chemical: Mapped[KpiChemical] = relationship(back_populates="station_requirements")
    __table_args__ = (UniqueConstraint("station_id", "chemical_id", name="uq_station_chemical_requirement"),)


class ChemicalInspectionEntry(Base, ChemicalTimestampMixin):
    __tablename__ = "chemical_inspection_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False, index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("kpi_chemicals.id"), nullable=False)
    required_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    actual_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    shortfall_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    excess_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    availability_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    remarks: Mapped[str | None] = mapped_column(Text)
    captured_latitude: Mapped[float | None] = mapped_column(Float)
    captured_longitude: Mapped[float | None] = mapped_column(Float)
    gps_accuracy: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    chemical: Mapped[KpiChemical] = relationship()
    __table_args__ = (UniqueConstraint("inspection_id", "chemical_id", name="uq_chemical_inspection_entry"),)
