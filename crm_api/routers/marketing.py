from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from database.db import get_db_session
from crm_api.dependencies import get_current_user
from database.models_crm import (
    MarketingCampaign, CampaignAudience, CampaignMessage, CampaignRun, ClientChannelPreference, CampaignDelivery, User, ClientAction
)
import json
from datetime import datetime

router = APIRouter()


class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "draft"
    channel: Optional[str] = "both"
    schedule_at: Optional[datetime] = None
    params: Optional[dict] = None


class CampaignResponse(CampaignBase):
    id: int
    class Config:
        from_attributes = True


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    res = []
    for c in db.query(MarketingCampaign).order_by(MarketingCampaign.created_at.desc()).all():
        res.append(
            CampaignResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                status=c.status,
                channel=c.channel,
                schedule_at=c.schedule_at,
                params=json.loads(c.params) if c.params else None,
            )
        )
    return res


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    c = MarketingCampaign(
        name=payload.name,
        description=payload.description,
        status=payload.status or "draft",
        channel=payload.channel or "both",
        schedule_at=payload.schedule_at,
        params=json.dumps(payload.params, ensure_ascii=False) if payload.params else None,
        created_by=current_user.id if current_user else None,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return CampaignResponse(
        id=c.id,
        name=c.name,
        description=c.description,
        status=c.status,
        channel=c.channel,
        schedule_at=c.schedule_at,
        params=payload.params,
    )


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    payload: CampaignBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    c = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    c.name = payload.name
    c.description = payload.description
    c.status = payload.status or c.status
    c.channel = payload.channel or c.channel
    c.schedule_at = payload.schedule_at
    c.params = json.dumps(payload.params, ensure_ascii=False) if payload.params else None
    c.updated_by = current_user.id if current_user else None
    db.commit()
    db.refresh(c)
    return CampaignResponse(
        id=c.id,
        name=c.name,
        description=c.description,
        status=c.status,
        channel=c.channel,
        schedule_at=c.schedule_at,
        params=payload.params,
    )


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)
):
    c = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    # Soft-constraint: Disallow deletion if runs exist (basic rule)
    has_runs = db.query(CampaignRun).filter(CampaignRun.campaign_id == campaign_id).first()
    if has_runs:
        raise HTTPException(status_code=400, detail="Campaign has runs; cancel or complete instead of delete")
    db.delete(c)
    db.commit()
    return


# ---------------- Audiences ----------------
class AudienceBase(BaseModel):
    name: str
    description: str | None = None
    filter_json: dict | None = None

class AudienceResponse(AudienceBase):
    id: int
    class Config:
        from_attributes = True

@router.get("/audiences", response_model=list[AudienceResponse])
async def list_audiences(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    res = []
    for a in db.query(CampaignAudience).order_by(CampaignAudience.created_at.desc()).all():
        res.append(
            AudienceResponse(
                id=a.id,
                name=a.name,
                description=a.description,
                filter_json=(json.loads(a.filter_json) if a.filter_json else None),
            )
        )
    return res

@router.post("/audiences", response_model=AudienceResponse, status_code=status.HTTP_201_CREATED)
async def create_audience(payload: AudienceBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    a = CampaignAudience(
        name=payload.name,
        description=payload.description,
        filter_json=json.dumps(payload.filter_json, ensure_ascii=False) if payload.filter_json else None,
        created_by=current_user.id if current_user else None,
    )
    db.add(a); db.commit(); db.refresh(a)
    return AudienceResponse(id=a.id, name=a.name, description=a.description, filter_json=payload.filter_json)

@router.put("/audiences/{audience_id}", response_model=AudienceResponse)
async def update_audience(audience_id: int, payload: AudienceBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    a = db.query(CampaignAudience).filter(CampaignAudience.id == audience_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Audience not found")
    a.name = payload.name
    a.description = payload.description
    a.filter_json = json.dumps(payload.filter_json, ensure_ascii=False) if payload.filter_json else None
    a.updated_by = current_user.id if current_user else None
    db.commit(); db.refresh(a)
    return AudienceResponse(id=a.id, name=a.name, description=a.description, filter_json=payload.filter_json)

@router.delete("/audiences/{audience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audience(audience_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    a = db.query(CampaignAudience).filter(CampaignAudience.id == audience_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Audience not found")
    db.delete(a); db.commit()
    return


# ---------------- Messages ----------------
class MessageBase(BaseModel):
    campaign_id: int
    title: str | None = None
    body_text: str

class MessageResponse(MessageBase):
    id: int
    class Config:
        from_attributes = True

@router.get("/messages", response_model=list[MessageResponse])
async def list_messages(campaign_id: int | None = None, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    q = db.query(CampaignMessage)
    if campaign_id:
        q = q.filter(CampaignMessage.campaign_id == campaign_id)
    res = []
    for m in q.order_by(CampaignMessage.created_at.desc()).all():
        res.append(MessageResponse(id=m.id, campaign_id=m.campaign_id, title=m.title, body_text=m.body_text))
    return res

@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(payload: MessageBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    m = CampaignMessage(campaign_id=payload.campaign_id, title=payload.title, body_text=payload.body_text)
    db.add(m); db.commit(); db.refresh(m)
    return MessageResponse(id=m.id, campaign_id=m.campaign_id, title=m.title, body_text=m.body_text)

@router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(message_id: int, payload: MessageBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    m = db.query(CampaignMessage).filter(CampaignMessage.id == message_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    m.campaign_id = payload.campaign_id
    m.title = payload.title
    m.body_text = payload.body_text
    db.commit(); db.refresh(m)
    return MessageResponse(id=m.id, campaign_id=m.campaign_id, title=m.title, body_text=m.body_text)

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    m = db.query(CampaignMessage).filter(CampaignMessage.id == message_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(m); db.commit()
    return


# ---------------- Runs (start once) ----------------
class RunStartRequest(BaseModel):
    audience_id: int | None = None
    limit: int | None = 100

@router.post("/campaigns/{campaign_id}/start", status_code=status.HTTP_201_CREATED)
async def start_campaign_run(campaign_id: int, payload: RunStartRequest, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    from services.marketing_service import MarketingService
    c = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    audience = None
    if payload.audience_id:
        audience = db.query(CampaignAudience).filter(CampaignAudience.id == payload.audience_id).first()
        if not audience:
            raise HTTPException(status_code=404, detail="Audience not found")
    run = CampaignRun(campaign_id=campaign_id, audience_id=payload.audience_id, status="running", started_at=datetime.utcnow())
    db.add(run); db.commit(); db.refresh(run)

    # Process synchronously (first iteration). Later: background/cron.
    processed = MarketingService.process_run(db, run, limit=payload.limit or 100)

    run.status = "completed"
    run.completed_at = datetime.utcnow()
    db.commit(); db.refresh(run)

    return {"run_id": run.id, "processed": processed, "sent": run.sent, "errors": run.errors}


@router.get("/campaigns/{campaign_id}/runs")
async def list_campaign_runs(campaign_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    runs = (
        db.query(CampaignRun)
        .filter(CampaignRun.campaign_id == campaign_id)
        .order_by(CampaignRun.started_at.desc().nullslast())
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "total": r.total,
            "sent": r.sent,
            "errors": r.errors,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get("/campaigns/{campaign_id}/deliveries")
async def list_campaign_deliveries(campaign_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    qs = (
        db.query(CampaignDelivery)
        .filter(CampaignDelivery.campaign_id == campaign_id)
        .order_by(CampaignDelivery.created_at.desc())
        .limit(500)
        .all()
    )
    return [
        {
            "id": d.id,
            "run_id": d.run_id,
            "client_id": d.client_id,
            "channel": d.channel,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in qs
    ]


@router.get("/campaigns/{campaign_id}/summary")
async def get_campaign_summary(
    campaign_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    total_runs = db.query(CampaignRun).filter(CampaignRun.campaign_id == campaign_id).count()
    last_run = (
        db.query(CampaignRun)
        .filter(CampaignRun.campaign_id == campaign_id)
        .order_by(CampaignRun.started_at.desc().nullslast())
        .first()
    )
    deliveries = db.query(CampaignDelivery).filter(CampaignDelivery.campaign_id == campaign_id).all()
    unique_clients = len(set(d.client_id for d in deliveries))
    sent_total = sum(1 for d in deliveries if d.status == "sent")
    failed_total = sum(1 for d in deliveries if d.status == "failed")
    by_channel = {}
    for d in deliveries:
        ch = d.channel or "unknown"
        if ch not in by_channel:
            by_channel[ch] = {"sent": 0, "failed": 0, "total": 0}
        by_channel[ch]["total"] += 1
        if d.status == "sent":
            by_channel[ch]["sent"] += 1
        elif d.status == "failed":
            by_channel[ch]["failed"] += 1
    # Conversions: count clients with PAYMENT_RECEIVED action after any delivery
    delivered_client_ids = list(set(d.client_id for d in deliveries))
    conversions = 0
    if delivered_client_ids:
        conversions = (
            db.query(ClientAction)
            .filter(
                ClientAction.client_id.in_(delivered_client_ids),
                ClientAction.action_type == "payment_received",
            )
            .count()
        )
    conversion_rate = (conversions / unique_clients) if unique_clients > 0 else 0.0

    return {
        "campaign_id": campaign_id,
        "total_runs": total_runs,
        "last_run_started_at": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
        "unique_clients": unique_clients,
        "sent_total": sent_total,
        "failed_total": failed_total,
        "by_channel": by_channel,
        "conversions": conversions,
        "conversion_rate": conversion_rate,
    }


@router.get("/campaigns/{campaign_id}/timeseries")
async def get_campaign_timeseries(
    campaign_id: int,
    days: int = 7,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Simple time series of deliveries by day for the last N days.
    Returns [{ date: 'YYYY-MM-DD', total, sent, failed, telegram, email }].
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 60)))
    qs = (
        db.query(CampaignDelivery)
        .filter(CampaignDelivery.campaign_id == campaign_id)
        .filter(CampaignDelivery.created_at >= since)
        .order_by(CampaignDelivery.created_at.asc())
        .all()
    )
    bucket: dict[str, dict] = {}
    for d in qs:
        dt = d.created_at or datetime.utcnow()
        key = dt.strftime("%Y-%m-%d")
        if key not in bucket:
            bucket[key] = {"date": key, "total": 0, "sent": 0, "failed": 0, "telegram": 0, "email": 0}
        bucket[key]["total"] += 1
        if d.status == "sent":
            bucket[key]["sent"] += 1
        elif d.status == "failed":
            bucket[key]["failed"] += 1
        ch = (d.channel or "").lower()
        if ch in ("telegram", "email"):
            bucket[key][ch] += 1
    series = list(bucket.values())
    series.sort(key=lambda x: x["date"])
    return {"series": series}

@router.post("/process-scheduled")
async def process_scheduled_campaigns(
    limit_per_run: int = 200,
    max_runs: int = 5,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    from services.marketing_service import MarketingService
    started = MarketingService.process_scheduled(db, limit_per_run=limit_per_run, max_runs=max_runs)
    return {"started_runs": started}


# ---------------- Client Channel Preferences ----------------
class PreferencePayload(BaseModel):
    allow_telegram: bool | None = None
    allow_email: bool | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None

@router.get("/preferences/{client_id}")
async def get_client_preferences(client_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    pref = db.query(ClientChannelPreference).filter(ClientChannelPreference.client_id == client_id).first()
    if not pref:
        return {
            "client_id": client_id,
            "allow_telegram": True,
            "allow_email": True,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
        }
    return {
        "client_id": client_id,
        "allow_telegram": pref.allow_telegram,
        "allow_email": pref.allow_email,
        "quiet_hours_start": pref.quiet_hours_start,
        "quiet_hours_end": pref.quiet_hours_end,
    }

@router.put("/preferences/{client_id}")
async def update_client_preferences(
    client_id: int,
    payload: PreferencePayload,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    pref = db.query(ClientChannelPreference).filter(ClientChannelPreference.client_id == client_id).first()
    if not pref:
        pref = ClientChannelPreference(client_id=client_id)
        db.add(pref)
    if payload.allow_telegram is not None:
        pref.allow_telegram = payload.allow_telegram
    if payload.allow_email is not None:
        pref.allow_email = payload.allow_email
    if payload.quiet_hours_start is not None:
        pref.quiet_hours_start = payload.quiet_hours_start
    if payload.quiet_hours_end is not None:
        pref.quiet_hours_end = payload.quiet_hours_end
    db.commit(); db.refresh(pref)
    return {
        "client_id": client_id,
        "allow_telegram": pref.allow_telegram,
        "allow_email": pref.allow_email,
        "quiet_hours_start": pref.quiet_hours_start,
        "quiet_hours_end": pref.quiet_hours_end,
    }

