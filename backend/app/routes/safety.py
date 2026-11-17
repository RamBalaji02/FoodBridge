
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import MetaData, Table, select, update, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin


router = APIRouter(
    prefix="/safety",
    tags=["Food Safety"],
)

metadata = MetaData()

donations = Table(
    "donations",
    metadata,
    autoload_with=__import__(
        "app.core.database",
        fromlist=["engine"]
    ).engine,
)


# --------------------------------------------------
# FOOD SAFETY ALERTS
# --------------------------------------------------

@router.get("/alerts")
def get_food_safety_alerts(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    now = datetime.now()
    warning_time = now + timedelta(hours=2)

    # Find expired available donations
    expired_donations = db.execute(
        select(
            donations.c.id,
            donations.c.title,
            donations.c.quantity,
            donations.c.unit,
            donations.c.expires_at,
            donations.c.pickup_city,
        )
        .where(
            donations.c.status == "AVAILABLE",
            donations.c.expires_at <= now,
        )
        .order_by(donations.c.expires_at.asc())
    ).mappings().all()

    # Find donations expiring within 2 hours
    expiring_soon = db.execute(
        select(
            donations.c.id,
            donations.c.title,
            donations.c.quantity,
            donations.c.unit,
            donations.c.expires_at,
            donations.c.pickup_city,
        )
        .where(
            donations.c.status == "AVAILABLE",
            donations.c.expires_at > now,
            donations.c.expires_at <= warning_time,
        )
        .order_by(donations.c.expires_at.asc())
    ).mappings().all()

    # Mark expired donations
    if expired_donations:
        expired_ids = [item["id"] for item in expired_donations]

        db.execute(
            update(donations)
            .where(donations.c.id.in_(expired_ids))
            .values(
                status="EXPIRED",
                updated_at=now,
            )
        )

        db.commit()

    return {
        "total_expired": len(expired_donations),
        "total_expiring_soon": len(expiring_soon),
        "expired_donations": [dict(item) for item in expired_donations],
        "expiring_soon": [dict(item) for item in expiring_soon],
    }


# --------------------------------------------------
# FOOD SAFETY SUMMARY
# --------------------------------------------------

@router.get("/summary")
def get_food_safety_summary(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    total_expired = db.execute(
        select(func.count())
        .select_from(donations)
        .where(donations.c.status == "EXPIRED")
    ).scalar() or 0

    total_available = db.execute(
        select(func.count())
        .select_from(donations)
        .where(donations.c.status == "AVAILABLE")
    ).scalar() or 0

    return {
        "expired_donations": total_expired,
        "available_donations": total_available,
    }
