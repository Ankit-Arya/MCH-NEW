from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.all_models import Inspection, InspectionReview, InspectionStatus, InspectionWorkflowHistory, ReviewAction, RoleCode, User
from app.core.permissions import DGM_ROLES, LINE_MANAGER_ROLES, require_inspection_access, require_roles
from app.schemas.review import ReviewIn
from app.services.audit_service import audit_log


FINAL_GM_APPROVED_STATUS = InspectionStatus.DGM_APPROVED
FINAL_GM_REJECTED_STATUS = InspectionStatus.DGM_REJECTED


def _add_review_and_history(
    db: Session,
    *,
    inspection: Inspection,
    payload: ReviewIn,
    user: User,
    review_level: str,
    audit_action: str,
    old_status: str,
) -> InspectionReview:
    review = InspectionReview(
        inspection_id=inspection.id,
        reviewer_id=user.id,
        reviewer_role=user.role.code.value,
        review_level=review_level,
        **payload.model_dump(),
    )
    db.add(review)
    db.add(
        InspectionWorkflowHistory(
            inspection_id=inspection.id,
            from_status=old_status,
            to_status=inspection.status.value,
            action_by=user.id,
            action=payload.action.value,
            remarks=payload.comments,
        )
    )
    audit_log(db, actor=user, action=audit_action, entity_type="Inspection", entity_id=inspection.id)
    db.commit()
    db.refresh(review)
    return review


def review_by_line_manager(db: Session, inspection: Inspection, payload: ReviewIn, user: User) -> InspectionReview:
    """LM/AM can only return for clarification or forward to DGM."""
    require_roles(user, LINE_MANAGER_ROLES | {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    require_inspection_access(db, user, inspection)
    if inspection.status != InspectionStatus.UNDER_LINE_MANAGER_REVIEW:
        raise HTTPException(status_code=400, detail="Inspection is not pending LM/AM review")

    old = inspection.status.value
    if payload.action == ReviewAction.RETURN_FOR_CLARIFICATION:
        inspection.status = InspectionStatus.RETURNED_FOR_CLARIFICATION
    elif payload.action == ReviewAction.RECOMMEND_PENALTY:
        inspection.status = InspectionStatus.LINE_MANAGER_RECOMMENDED
    else:
        raise HTTPException(status_code=400, detail="LM/AM can only forward to DGM or return for clarification")

    return _add_review_and_history(
        db,
        inspection=inspection,
        payload=payload,
        user=user,
        review_level="LINE_MANAGER",
        audit_action="LINE_MANAGER_REVIEW",
        old_status=old,
    )


def review_by_dgm(db: Session, inspection: Inspection, payload: ReviewIn, user: User) -> InspectionReview:
    """DGM can only return for clarification or forward to GM/Ops.

    DGM approval/rejection is deliberately blocked because final approval/rejection
    belongs to GM/Ops only.
    """
    require_roles(user, DGM_ROLES | {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    require_inspection_access(db, user, inspection)
    if inspection.status != InspectionStatus.LINE_MANAGER_RECOMMENDED:
        raise HTTPException(status_code=400, detail="Inspection is not pending DGM review")

    old = inspection.status.value
    if payload.action == ReviewAction.RETURN_FOR_CLARIFICATION:
        inspection.status = InspectionStatus.RETURNED_FOR_CLARIFICATION
    elif payload.action == ReviewAction.SEND_TO_GM:
        inspection.status = InspectionStatus.GM_REVIEW_REQUIRED
    else:
        raise HTTPException(status_code=400, detail="DGM can only forward to GM/Ops or return for clarification")

    return _add_review_and_history(
        db,
        inspection=inspection,
        payload=payload,
        user=user,
        review_level="DGM",
        audit_action="DGM_REVIEW",
        old_status=old,
    )


def review_by_gm(db: Session, inspection: Inspection, payload: ReviewIn, user: User) -> InspectionReview:
    """GM/Ops gives final approval or final rejection.

    The existing terminal enum values DGM_APPROVED/DGM_REJECTED are reused for
    backward DB compatibility, but this service now writes them only from GM/Ops
    action and UI/PDF labels display them as final GM/Ops decisions.
    """
    require_roles(user, {RoleCode.GM_OPS, RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    if inspection.status != InspectionStatus.GM_REVIEW_REQUIRED:
        raise HTTPException(status_code=400, detail="Inspection is not pending GM/Ops final review")

    old = inspection.status.value
    if payload.action == ReviewAction.APPROVE:
        inspection.status = FINAL_GM_APPROVED_STATUS
    elif payload.action == ReviewAction.REJECT:
        inspection.status = FINAL_GM_REJECTED_STATUS
    else:
        raise HTTPException(status_code=400, detail="GM/Ops can only finally approve or finally reject")

    return _add_review_and_history(
        db,
        inspection=inspection,
        payload=payload,
        user=user,
        review_level="GM",
        audit_action="GM_FINAL_REVIEW",
        old_status=old,
    )
