
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, select, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user
from app.schemas.volunteer import (
    VolunteerProfileCreate,
    VolunteerAvailabilityUpdate
)

router = APIRouter(prefix="/volunteer", tags=["Volunteer"])

metadata = MetaData()

volunteer_profiles = Table(
    "volunteer_profiles",
    metadata,
    autoload_with=engine
)


def check_volunteer(user):
    if user["role"] != "VOLUNTEER":
        raise HTTPException(
            status_code=403,
            detail="Only volunteers can access this feature."
        )


@router.post("/profile", status_code=status.HTTP_201_CREATED)
def create_volunteer_profile(
    data: VolunteerProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    check_volunteer(current_user)

    existing = db.execute(
        select(volunteer_profiles.c.id).where(
            volunteer_profiles.c.user_id == current_user["id"]
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Volunteer profile already exists."
        )

    try:
        result = db.execute(
            insert(volunteer_profiles)
            .values(
                user_id=current_user["id"],
                vehicle_type=data.vehicle_type.strip(),
                vehicle_number=data.vehicle_number,
                is_available=True,
                city=data.city.strip(),
                emergency_contact=data.emergency_contact.strip()
            )
            .returning(volunteer_profiles)
        )

        profile = result.mappings().one()
        db.commit()

        return {
            "message": "Volunteer profile created successfully.",
            "profile": dict(profile)
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create volunteer profile."
        )


@router.get("/profile")
def get_volunteer_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    check_volunteer(current_user)

    profile = db.execute(
        select(volunteer_profiles).where(
            volunteer_profiles.c.user_id == current_user["id"]
        )
    ).mappings().first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Volunteer profile not found."
        )

    return dict(profile)


@router.patch("/availability")
def update_availability(
    data: VolunteerAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    check_volunteer(current_user)

    result = db.execute(
        update(volunteer_profiles)
        .where(
            volunteer_profiles.c.user_id == current_user["id"]
        )
        .values(is_available=data.is_available)
        .returning(volunteer_profiles)
    )

    profile = result.mappings().first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Create your volunteer profile first."
        )

    db.commit()

    return {
        "message": "Availability updated successfully.",
        "is_available": profile["is_available"]
    }
