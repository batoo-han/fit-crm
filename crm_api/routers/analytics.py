"""Analytics router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db_session
from database.models import Client, Payment, TrainingProgram
from database.models_crm import PipelineStage, User
from crm_api.dependencies import get_current_user
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/overview")
async def get_overview(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get overview statistics."""
    total_clients = db.query(Client).count()
    active_clients = db.query(Client).filter(Client.status == "client").count()
    total_programs = db.query(TrainingProgram).count()
    paid_programs = db.query(TrainingProgram).filter(TrainingProgram.is_paid == True).count()
    
    # Revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "completed"
    ).scalar() or 0
    
    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "total_programs": total_programs,
        "paid_programs": paid_programs,
        "total_revenue": float(total_revenue),
    }


@router.get("/conversion")
async def get_conversion_analytics(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get conversion funnel analytics."""
    stages = db.query(PipelineStage).filter(PipelineStage.is_active == True).order_by(PipelineStage.order).all()
    
    conversion_data = []
    for stage in stages:
        count = db.query(Client).filter(Client.pipeline_stage_id == stage.id).count()
        conversion_data.append({
            "stage_id": stage.id,
            "stage_name": stage.name,
            "count": count,
            "color": stage.color
        })
    
    return conversion_data


@router.get("/revenue")
async def get_revenue_analytics(
    days: int = 30,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get revenue analytics."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    payments = db.query(Payment).filter(
        Payment.status == "completed",
        Payment.completed_at >= start_date
    ).all()
    
    total_revenue = sum(p.amount for p in payments)
    
    return {
        "period_days": days,
        "total_revenue": float(total_revenue),
        "payment_count": len(payments),
        "average_payment": float(total_revenue / len(payments)) if payments else 0
    }

