
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, select, insert, update, func
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user
from app.schemas.donation import DonationCreate


router = APIRouter(prefix="/donations", tags=["Donations"])

metadata = MetaData()

donations = Table("donations", metadata, autoload_with=engine)
categories = Table("food_categories", metadata, autoload_with=engine)
donor_profiles = Table("donor_profiles", metadata, autoload_with=engine)


def require_donor(user):
    if user["role"] != "DONOR":
        raise HTTPException(403, "Only donors can manage donations.")

    if not user["is_active"]:
        raise HTTPException(403, "Account is not active.")


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_donation(
    data: DonationCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_donor(user)

    profile = db.execute(
        select(donor_profiles.c.user_id).where(
            donor_profiles.c.user_id == user["id"]
        )
    ).first()

    if not profile:
        raise HTTPException(400, "Create your donor profile first.")

    category = db.execute(
        select(categories.c.id).where(
            categories.c.id == data.category_id
        )
    ).first()

    if not category:
        raise HTTPException(404, "Food category not found.")

    if data.prepared_at.tzinfo is None or data.expires_at.tzinfo is None:
        raise HTTPException(400, "Preparation and expiry times must include timezone.")

    if data.prepared_at > datetime.now(timezone.utc):
        raise HTTPException(400, "Preparation time cannot be in the future.")

    now = datetime.now(timezone.utc)

    values = data.model_dump()
    values["donor_id"] = user["id"]
    values["status"] = "AVAILABLE"
    values["created_at"] = now
    values["updated_at"] = now

    result = db.execute(
        insert(donations).values(**values).returning(donations)
    )

    new_donation = result.mappings().one()
    db.commit()

    return {
        "message": "Food donation created successfully.",
        "donation": dict(new_donation),
    }


@router.get("/my")
def get_my_donations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_donor(user)

    rows = db.execute(
        select(donations)
        .where(donations.c.donor_id == user["id"])
        .order_by(donations.c.created_at.desc())
    ).mappings().all()

    return {"total": len(rows), "donations": [dict(row) for row in rows]}


@router.get("/available")
def get_available_donations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user["role"] not in ["NGO", "ADMIN"]:
        raise HTTPException(403, "Only NGOs can view available donations.")

    now = datetime.now(timezone.utc)

    rows = db.execute(
        select(donations)
        .where(
            donations.c.status == "AVAILABLE",
            donations.c.expires_at > now,
        )
        .order_by(donations.c.expires_at.asc())
    ).mappings().all()

    return {"total": len(rows), "donations": [dict(row) for row in rows]}


@router.patch("/{donation_id}")
def update_donation(
    donation_id: int,
    data: DonationCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_donor(user)

    existing = db.execute(
        select(donations).where(
            donations.c.id == donation_id,
            donations.c.donor_id == user["id"],
        )
    ).mappings().first()

    if not existing:
        raise HTTPException(404, "Donation not found.")

    if existing["status"] != "AVAILABLE":
        raise HTTPException(400, "Only available donations can be edited.")

    if data.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(400, "Expiry time must be in the future.")

    category = db.execute(
        select(categories.c.id).where(categories.c.id == data.category_id)
    ).first()

    if not category:
        raise HTTPException(404, "Food category not found.")

    values = data.model_dump()
    values["updated_at"] = datetime.now(timezone.utc)

    db.execute(
        update(donations)
        .where(donations.c.id == donation_id)
        .values(**values)
    )
    db.commit()

    return {"message": "Donation updated successfully.", "donation_id": donation_id}


@router.delete("/{donation_id}")
def cancel_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_donor(user)

    existing = db.execute(
        select(donations).where(
            donations.c.id == donation_id,
            donations.c.donor_id == user["id"],
        )
    ).mappings().first()

    if not existing:
        raise HTTPException(404, "Donation not found.")

    if existing["status"] != "AVAILABLE":
        raise HTTPException(400, "Only available donations can be cancelled.")

    db.execute(
        update(donations)
        .where(donations.c.id == donation_id)
        .values(
            status="CANCELLED",
            cancellation_reason="Cancelled by donor",
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    return {"message": "Donation cancelled successfully."}
