import enum
from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RoleCode(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    HK_CELL_ADMIN = "HK_CELL_ADMIN"
    GM_OPS = "GM_OPS"
    DGM_LINE = "DGM_LINE"
    DGM_HK = "DGM_HK"
    AM_MGR_LINE = "AM_MGR_LINE"
    AM_MGR_HK = "AM_MGR_HK"
    STATION_MANAGER = "STATION_MANAGER"
    EIT_MEMBER = "EIT_MEMBER"
    AUDITOR = "AUDITOR"


class InspectionType(str, enum.Enum):
    SM_INSPECTION = "SM_INSPECTION"
    EIT_INSPECTION = "EIT_INSPECTION"
    SPECIAL_INSPECTION = "SPECIAL_INSPECTION"
    RE_INSPECTION = "RE_INSPECTION"


class InspectionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_LINE_MANAGER_REVIEW = "UNDER_LINE_MANAGER_REVIEW"
    RETURNED_FOR_CLARIFICATION = "RETURNED_FOR_CLARIFICATION"
    LINE_MANAGER_RECOMMENDED = "LINE_MANAGER_RECOMMENDED"
    DGM_APPROVED = "DGM_APPROVED"
    DGM_REJECTED = "DGM_REJECTED"
    GM_REVIEW_REQUIRED = "GM_REVIEW_REQUIRED"
    GM_REVIEWED = "GM_REVIEWED"
    CLOSED = "CLOSED"


class ReviewAction(str, enum.Enum):
    COMMENT = "COMMENT"
    RETURN_FOR_CLARIFICATION = "RETURN_FOR_CLARIFICATION"
    RECOMMEND_PENALTY = "RECOMMEND_PENALTY"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SEND_TO_GM = "SEND_TO_GM"
    GM_REVIEW = "GM_REVIEW"


class MediaType(str, enum.Enum):
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[RoleCode] = mapped_column(Enum(RoleCode), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority_level: Mapped[int] = mapped_column(Integer, default=100)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    emp_number: Mapped[str | None] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    mobile: Mapped[str | None] = mapped_column(String(20))
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    role: Mapped[Role] = relationship(back_populates="users")
    station_access: Mapped[list["UserStationAccess"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    line_access: Mapped[list["UserLineAccess"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Line(Base, TimestampMixin):
    __tablename__ = "lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    line_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    line_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    stations: Mapped[list["Station"]] = relationship(back_populates="line")


class Station(Base, TimestampMixin):
    __tablename__ = "stations"
    id: Mapped[int] = mapped_column(primary_key=True)
    station_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    station_name: Mapped[str] = mapped_column(String(150), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("lines.id"), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    line: Mapped[Line] = relationship(back_populates="stations")
    contract_mappings: Mapped[list["ContractStation"]] = relationship(back_populates="station")


class Contractor(Base, TimestampMixin):
    __tablename__ = "contractors"
    id: Mapped[int] = mapped_column(primary_key=True)
    contractor_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contractor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(150))
    mobile: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    contracts: Mapped[list["Contract"]] = relationship(back_populates="contractor")


class GradingScheme(Base, TimestampMixin):
    __tablename__ = "grading_schemes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    options: Mapped[list["GradingOption"]] = relationship(back_populates="scheme", cascade="all, delete-orphan")


class GradingOption(Base, TimestampMixin):
    __tablename__ = "grading_options"
    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("grading_schemes.id"), nullable=False)
    grade_code: Mapped[str] = mapped_column(String(5), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)

    scheme: Mapped[GradingScheme] = relationship(back_populates="options")
    __table_args__ = (UniqueConstraint("scheme_id", "grade_code", name="uq_grade_scheme_code"),)


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    tender_no: Mapped[str | None] = mapped_column(String(120))
    contract_name: Mapped[str] = mapped_column(String(250), nullable=False)
    contractor_id: Mapped[int] = mapped_column(ForeignKey("contractors.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    extension_end_date: Mapped[date | None] = mapped_column(Date)
    monthly_bill_value_default: Mapped[float] = mapped_column(Float, default=0)
    grading_scheme_id: Mapped[int] = mapped_column(ForeignKey("grading_schemes.id"), nullable=False)
    kpi6_threshold_percent: Mapped[float] = mapped_column(Float, default=90)
    kpi6_penalty_percent: Mapped[float] = mapped_column(Float, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    contractor: Mapped[Contractor] = relationship(back_populates="contracts")
    grading_scheme: Mapped[GradingScheme] = relationship()
    station_mappings: Mapped[list["ContractStation"]] = relationship(back_populates="contract", cascade="all, delete-orphan")


class ContractStation(Base, TimestampMixin):
    __tablename__ = "contract_stations"
    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    contract: Mapped[Contract] = relationship(back_populates="station_mappings")
    station: Mapped[Station] = relationship(back_populates="contract_mappings")
    __table_args__ = (UniqueConstraint("contract_id", "station_id", name="uq_contract_station"),)


class UserStationAccess(Base, TimestampMixin):
    __tablename__ = "user_station_access"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="station_access")
    station: Mapped[Station] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "station_id", name="uq_user_station"),)


class UserLineAccess(Base, TimestampMixin):
    __tablename__ = "user_line_access"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("lines.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="line_access")
    line: Mapped[Line] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "line_id", name="uq_user_line"),)


class InspectionAttribute(Base, TimestampMixin):
    __tablename__ = "inspection_attributes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sub_areas: Mapped[list["InspectionSubArea"]] = relationship(back_populates="attribute", cascade="all, delete-orphan")


class InspectionSubArea(Base, TimestampMixin):
    __tablename__ = "inspection_sub_areas"
    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("inspection_attributes.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    photo_min_required: Mapped[int] = mapped_column(Integer, default=1)
    photo_max_allowed: Mapped[int] = mapped_column(Integer, default=3)
    video_required: Mapped[bool] = mapped_column(Boolean, default=False)
    video_max_seconds: Mapped[int] = mapped_column(Integer, default=15)
    allow_na: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    attribute: Mapped[InspectionAttribute] = relationship(back_populates="sub_areas")


class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    inspection_type: Mapped[InspectionType] = mapped_column(Enum(InspectionType), nullable=False)
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    gps_accuracy: Mapped[float | None] = mapped_column(Float)
    device_info: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[InspectionStatus] = mapped_column(Enum(InspectionStatus), default=InspectionStatus.DRAFT, index=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    is_before_10am: Mapped[bool] = mapped_column(Boolean, default=False)
    remarks: Mapped[str | None] = mapped_column(Text)

    contract: Mapped[Contract] = relationship()
    station: Mapped[Station] = relationship()
    submitter: Mapped[User] = relationship()
    attribute_scores: Mapped[list["InspectionAttributeScore"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    observations: Mapped[list["InspectionSubAreaObservation"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    media: Mapped[list["InspectionMedia"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    reviews: Mapped[list["InspectionReview"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")


class InspectionAttributeScore(Base, TimestampMixin):
    __tablename__ = "inspection_attribute_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("inspection_attributes.id"), nullable=False)
    grade_code: Mapped[str] = mapped_column(String(5), nullable=False)
    grade_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)

    inspection: Mapped[Inspection] = relationship(back_populates="attribute_scores")
    attribute: Mapped[InspectionAttribute] = relationship()
    __table_args__ = (UniqueConstraint("inspection_id", "attribute_id", name="uq_inspection_attribute_score"),)


class InspectionSubAreaObservation(Base, TimestampMixin):
    __tablename__ = "inspection_sub_area_observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("inspection_attributes.id"), nullable=False)
    sub_area_id: Mapped[int] = mapped_column(ForeignKey("inspection_sub_areas.id"), nullable=False)
    is_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    na_reason: Mapped[str | None] = mapped_column(Text)
    observation_text: Mapped[str | None] = mapped_column(Text)

    inspection: Mapped[Inspection] = relationship(back_populates="observations")
    attribute: Mapped[InspectionAttribute] = relationship()
    sub_area: Mapped[InspectionSubArea] = relationship()
    __table_args__ = (UniqueConstraint("inspection_id", "sub_area_id", name="uq_inspection_sub_area"),)


class InspectionMedia(Base, TimestampMixin):
    __tablename__ = "inspection_media"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("inspection_attributes.id"), nullable=False)
    sub_area_id: Mapped[int] = mapped_column(ForeignKey("inspection_sub_areas.id"), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    object_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(250), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128), index=True)
    captured_latitude: Mapped[float | None] = mapped_column(Float)
    captured_longitude: Mapped[float | None] = mapped_column(Float)
    gps_accuracy: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    inspection: Mapped[Inspection] = relationship(back_populates="media")
    attribute: Mapped[InspectionAttribute] = relationship()
    sub_area: Mapped[InspectionSubArea] = relationship()
    uploader: Mapped[User] = relationship()


class InspectionReview(Base, TimestampMixin):
    __tablename__ = "inspection_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(80), nullable=False)
    review_level: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    recommended_penalty_amount: Mapped[float | None] = mapped_column(Float)
    final_penalty_amount: Mapped[float | None] = mapped_column(Float)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inspection: Mapped[Inspection] = relationship(back_populates="reviews")
    reviewer: Mapped[User] = relationship()


class InspectionWorkflowHistory(Base, TimestampMixin):
    __tablename__ = "inspection_workflow_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(80))
    to_status: Mapped[str] = mapped_column(String(80), nullable=False)
    action_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)

    inspection: Mapped[Inspection] = relationship()
    actor: Mapped[User] = relationship()


class BillingCycle(Base, TimestampMixin):
    __tablename__ = "billing_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class MonthlyBillValue(Base, TimestampMixin):
    __tablename__ = "monthly_bill_values"
    id: Mapped[int] = mapped_column(primary_key=True)
    billing_cycle_id: Mapped[int] = mapped_column(ForeignKey("billing_cycles.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    bill_value: Mapped[float] = mapped_column(Float, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (UniqueConstraint("billing_cycle_id", "contract_id", name="uq_bill_cycle_contract"),)


class MonthlyStationScore(Base, TimestampMixin):
    __tablename__ = "monthly_station_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    billing_cycle_id: Mapped[int] = mapped_column(ForeignKey("billing_cycles.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    sm_inspection_count: Mapped[int] = mapped_column(Integer, default=0)
    eit_inspection_count: Mapped[int] = mapped_column(Integer, default=0)
    sm_average_score: Mapped[float] = mapped_column(Float, default=0)
    eit_average_score: Mapped[float] = mapped_column(Float, default=0)
    final_station_score: Mapped[float] = mapped_column(Float, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("billing_cycle_id", "contract_id", "station_id", name="uq_station_month_score"),)


class MonthlyContractScore(Base, TimestampMixin):
    __tablename__ = "monthly_contract_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    billing_cycle_id: Mapped[int] = mapped_column(ForeignKey("billing_cycles.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    station_count: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[float] = mapped_column(Float, default=0)
    is_penalty_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("billing_cycle_id", "contract_id", name="uq_contract_month_score"),)


class PenaltyCalculation(Base, TimestampMixin):
    __tablename__ = "penalty_calculations"
    id: Mapped[int] = mapped_column(primary_key=True)
    billing_cycle_id: Mapped[int] = mapped_column(ForeignKey("billing_cycles.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    monthly_bill_value: Mapped[float] = mapped_column(Float, nullable=False)
    kpi_code: Mapped[str] = mapped_column(String(20), default="KPI6")
    kpi_score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_percentage: Mapped[float] = mapped_column(Float, default=90)
    penalty_percentage: Mapped[float] = mapped_column(Float, default=5)
    penalty_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="GENERATED")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("billing_cycle_id", "contract_id", "kpi_code", name="uq_penalty_cycle_contract_kpi"),)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(150), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    old_value_json: Mapped[dict | None] = mapped_column(JSON)
    new_value_json: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
