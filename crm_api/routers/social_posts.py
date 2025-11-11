from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from database.db import get_db_session
from crm_api.dependencies import get_current_user
from database.models_crm import SocialPost, SocialPostTemplate, User
from services.social_scheduler import SocialScheduler
from datetime import datetime, timedelta

router = APIRouter()


class SocialPostBase(BaseModel):
    platform: str = "telegram"
    title: Optional[str] = None
    content: str
    media_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = "draft"


class SocialPostResponse(SocialPostBase):
    id: int
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[SocialPostResponse])
async def list_posts(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    posts = SocialScheduler.list_posts(db, status_filter)
    return [SocialPostResponse.model_validate(p) for p in posts]


@router.post("", response_model=SocialPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: SocialPostBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    post = SocialPost(
        platform=payload.platform,
        title=payload.title,
        content=payload.content,
        media_url=payload.media_url,
        scheduled_at=payload.scheduled_at,
        status=payload.status or "draft",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return SocialPostResponse.model_validate(post)


@router.put("/{post_id}", response_model=SocialPostResponse)
async def update_post(
    post_id: int,
    payload: SocialPostBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.platform = payload.platform
    post.title = payload.title
    post.content = payload.content
    post.media_url = payload.media_url
    post.scheduled_at = payload.scheduled_at
    post.status = payload.status or post.status
    db.commit()
    db.refresh(post)
    return SocialPostResponse.model_validate(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return


@router.post("/process-scheduled")
async def process_scheduled_posts(
    limit: int = 10,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    processed = SocialScheduler.process_scheduled(db, limit=limit)
    return {"processed": processed}


@router.post("/{post_id}/retry", response_model=SocialPostResponse)
async def retry_post(
    post_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = "scheduled"
    post.scheduled_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return SocialPostResponse.model_validate(post)


@router.post("/{post_id}/duplicate", response_model=SocialPostResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_post(
    post_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    src = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Post not found")
    copy = SocialPost(
        platform=src.platform,
        title=src.title,
        content=src.content,
        media_url=src.media_url,
        scheduled_at=None,
        status="draft",
        error=None,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return SocialPostResponse.model_validate(copy)


# Bulk schedule
class BulkScheduleRequest(BaseModel):
    ids: list[int]
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = "scheduled"


@router.post("/bulk/schedule")
async def bulk_schedule(
    payload: BulkScheduleRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if not payload.ids:
        raise HTTPException(status_code=400, detail="No ids provided")
    q = db.query(SocialPost).filter(SocialPost.id.in__(payload.ids))
    updated = 0
    when = payload.scheduled_at or datetime.utcnow()
    for p in q.all():
        p.scheduled_at = when
        if payload.status:
            p.status = payload.status
        updated += 1
    db.commit()
    return {"updated": updated, "scheduled_at": when.isoformat()}


# Templates CRUD
class TemplateBase(BaseModel):
    name: str
    platform: Optional[str] = None
    title: Optional[str] = None
    content: str
    media_url: Optional[str] = None


class TemplateResponse(TemplateBase):
    id: int

    class Config:
        from_attributes = True


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(SocialPostTemplate).order_by(SocialPostTemplate.name.asc()).all()
    return [TemplateResponse.model_validate(r) for r in rows]


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if db.query(SocialPostTemplate).filter(SocialPostTemplate.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Template with this name already exists")
    row = SocialPostTemplate(
        name=payload.name,
        platform=payload.platform,
        title=payload.title,
        content=payload.content,
        media_url=payload.media_url,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TemplateResponse.model_validate(row)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    payload: TemplateBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    row = db.query(SocialPostTemplate).filter(SocialPostTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    row.name = payload.name
    row.platform = payload.platform
    row.title = payload.title
    row.content = payload.content
    row.media_url = payload.media_url
    db.commit()
    db.refresh(row)
    return TemplateResponse.model_validate(row)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    row = db.query(SocialPostTemplate).filter(SocialPostTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(row)
    db.commit()
    return

# Bulk sequential schedule
class BulkSequenceRequest(BaseModel):
    ids: list[int]
    start_at: datetime
    step_minutes: int = 60
    status: Optional[str] = "scheduled"
    quiet_hours_enabled: bool = False
    quiet_start: Optional[int] = 9   # hour 0-23
    quiet_end: Optional[int] = 21    # hour 0-23


@router.post("/bulk/sequence")
async def bulk_sequence(
    payload: BulkSequenceRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if not payload.ids:
        raise HTTPException(status_code=400, detail="No ids provided")
    if payload.step_minutes <= 0:
        raise HTTPException(status_code=400, detail="step_minutes must be > 0")
    if payload.quiet_hours_enabled:
        if payload.quiet_start is None or payload.quiet_end is None:
            raise HTTPException(status_code=400, detail="quiet_start and quiet_end required when quiet_hours_enabled")
        if not (0 <= payload.quiet_start <= 23 and 0 <= payload.quiet_end <= 23):
            raise HTTPException(status_code=400, detail="quiet hours must be between 0 and 23")

    def adjust(dt: datetime) -> datetime:
        if not payload.quiet_hours_enabled:
            return dt
        qs = int(payload.quiet_start or 0)
        qe = int(payload.quiet_end or 0)
        h = dt.hour
        # If quiet window is [qs, qe) not allowed to post; we move to first allowed hour
        if qs < qe:
            if qs <= h < qe:
                # move to qe today
                return dt.replace(hour=qe, minute=0, second=0, microsecond=0)
            return dt
        else:
            # window wraps midnight: [qs..23] U [0..qe)
            if h >= qs or h < qe:
                # move to qe today (if h<qe) or next day at qe (if h>=qs)
                if h < qe:
                    return dt.replace(hour=qe, minute=0, second=0, microsecond=0)
                else:
                    nxt = dt + timedelta(days=1)
                    return nxt.replace(hour=qe, minute=0, second=0, microsecond=0)
            return dt

    # Preserve order of ids as provided
    updated = 0
    current_time = payload.start_at
    for idx, pid in enumerate(payload.ids):
        post = db.query(SocialPost).filter(SocialPost.id == pid).first()
        if not post:
            continue
        candidate = current_time if idx == 0 else (payload.start_at + timedelta(minutes=payload.step_minutes * idx))
        candidate = adjust(candidate)
        post.scheduled_at = candidate
        if payload.status:
            post.status = payload.status
        updated += 1
    db.commit()
    return {"updated": updated}


class BulkApplyTemplateRequest(BaseModel):
    ids: list[int]
    template_id: int
    overwrite_title: bool = True
    overwrite_media: bool = True
    overwrite_platform: bool = False


@router.post("/bulk/apply-template")
async def bulk_apply_template(
    payload: BulkApplyTemplateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if not payload.ids:
        raise HTTPException(status_code=400, detail="No ids provided")
    tpl = db.query(SocialPostTemplate).filter(SocialPostTemplate.id == payload.template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    updated = 0
    for pid in payload.ids:
        post = db.query(SocialPost).filter(SocialPost.id == pid).first()
        if not post:
            continue
        if payload.overwrite_platform and tpl.platform:
            post.platform = tpl.platform
        if payload.overwrite_title:
            post.title = tpl.title
        post.content = tpl.content
        if payload.overwrite_media:
            post.media_url = tpl.media_url
        updated += 1
    db.commit()
    return {"updated": updated}


