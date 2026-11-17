from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user
from app.schemas.ngo import NGOProfileCreate

router = APIRouter(prefix="/ngo", tags=["NGO"])

metadata = MetaData()

ngo_profiles = Table(
    "ngo_profiles",
    metadata,
    autoload_with=engine
)


@router.post("/profile", status_code=status.HTTP_201_CREATED)
def create_ngo_profile(
    profile: NGOProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "NGO":
        raise HTTPException(
            status_code=403,
            detail="Only NGO accounts can create NGO profiles."
        )

    existing = db.execute(
        select(ngo_profiles.c.id).where(
            ngo_profiles.c.user_id == current_user["id"]
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="NGO profile already exists."
        )

    try:
        result = db.execute(
            insert(ngo_profiles)
            .values(
                user_id=current_user["id"],
                organization_name=profile.organization_name.strip(),
                registration_number=profile.registration_number,
                beneficiary_count=profile.beneficiary_count,
                storage_capacity_description=profile.storage_capacity_description,
                address=profile.address.strip(),
                city=profile.city.strip(),
                state=profile.state.strip(),
                postal_code=profile.postal_code.strip(),
                latitude=profile.latitude,
                longitude=profile.longitude,
                verification_status="PENDING"
            )
            .returning(ngo_profiles)
        )

        new_profile = result.mappings().one()
        db.commit()

        return {
            "message": "NGO profile created successfully.",
            "profile": dict(new_profile)
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create NGO profile."
        )


@router.get("/profile")
def get_ngo_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "NGO":
        raise HTTPException(
            status_code=403,
            detail="Only NGO accounts can access this profile."
        )

    profile = db.execute(
        select(ngo_profiles).where(
            ngo_profiles.c.user_id == current_user["id"]
        )
    ).mappings().first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="NGO profile not found."
        )

    return dict(profile)