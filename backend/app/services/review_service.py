from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.all_models import Inspection, InspectionReview, InspectionStatus, InspectionWorkflowHistory, ReviewAction, RoleCode, User
from app.core.permissions import DGM_ROLES, LINE_MANAGER_ROLES, require_inspection_access, require_roles
from app.schemas.review import ReviewIn
from app.services.audit_service import audit_log


def review_by_line_manager(db: Session, inspection: Inspection, payload: ReviewIn, user: User) -> InspectionReview:
    require_roles(user, LINE_MANAGER_ROLES | {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    require_inspection_access(db, user, inspection)
    if inspection.status != InspectionStatus.UNDER_LINE_MANAGER_REVIEW:
        raise HTTPException(status_code=400, detail="Inspection is not pending Line Manager review")
    old = inspection.status.value
    if payload.action == ReviewAction.RETURN_FOR_CLARIFICATION:
        inspection.status = InspectionStatus.RETURNED_FOR_CLARIFICATION
    elif payload.action == ReviewAction.RECOMMEND_PENALTY:
        inspection.status = InspectionStatus.LINE_MANAGER_RECOMMENDED
    else:
        raise HTTPException(status_code=400, detail="Invalid action for Line Manager review")
    review = InspectionReview(inspection_id=inspection.id, reviewer_id=user.id, reviewer_role=user.role.code.value, review_level="LINE_MANAGER", **payload.model_dump())
    db.add(review)
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=old, to_status=inspection.status.value, action_by=user.id, action=payload.action.value, remarks=payload.comments))
    audit_log(db, actor=user, action="LINE_MANAGER_REVIEW", entity_type="Inspection", entity_id=inspection.id)
    db.commit()
    db.refresh(review)
    return review


def review_by_dgm(db: Session, inspection: Inspection, payload: ReviewIn, user: User) -> InspectionReview:
    require_roles(user, DGM_ROLES | {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    require_inspection_access(db, user, inspection)
    if inspection.status != InspectionStatus.LINE_MANAGER_RECOMMENDED:
        raise HTTPException(status_code=400, detail="Inspection is not pending DGM review")
    old = inspection.status.value
    if payload.action == ReviewAction.APPROVE:
        inspection.status = InspectionStatus.DGM_APPROVED
    elif payload.action == ReviewAction.REJECT:
        inspection.status = InspectionStatus.DGM_REJECTED
    elif payload.action == ReviewAction.SEND_TO_GM:
        inspection.status = InspectionStatus.GM_REVIEW_REQUIRED
    else:
        raise HTTPException(status_code=400, detail="Invalid action for DGM review")
    review = InspectionReview(inspection_id=inspection.id, reviewer_id=user.id, reviewer_role=user.role.code.value, review_level="DGM", **payload.model_dump())
    db.add(review)
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=old, to_status=inspection.status.value, action_by=user.id, action=payload.action.value, remarks=payload.comments))
    audit_log(db, actor=user, action="DGM_REVIEW", entity_type="Inspection", entity_id=inspection.id)
    db.commit()
    db.refresh(review)
    return review


def review_by_gm(db: Session, inspection: Inspection, payload: ReviewIn, user: User) -> InspectionReview:
    require_roles(user, {RoleCode.GM_OPS, RoleCode.SUPER_ADMIN})
    # GM Ops is intentionally all-scope through role permissions.
    if inspection.status != InspectionStatus.GM_REVIEW_REQUIRED:
        raise HTTPException(status_code=400, detail="Inspection is not pending GM review")
    old = inspection.status.value
    inspection.status = InspectionStatus.GM_REVIEWED
    review = InspectionReview(inspection_id=inspection.id, reviewer_id=user.id, reviewer_role=user.role.code.value, review_level="GM", **payload.model_dump())
    db.add(review)
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=old, to_status=inspection.status.value, action_by=user.id, action="GM_REVIEW", remarks=payload.comments))
    audit_log(db, actor=user, action="GM_REVIEW", entity_type="Inspection", entity_id=inspection.id)
    db.commit()
    db.refresh(review)
    return review
