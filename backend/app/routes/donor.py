
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user
from app.schemas.donor import DonorProfileCreate


router = APIRouter(
    prefix="/donor",
    tags=["Donor"],
)

metadata = MetaData()

donor_profiles = Table(
    "donor_profiles",
    metadata,
    autoload_with=engine,
)


@router.post("/profile", status_code=status.HTTP_201_CREATED)
def create_donor_profile(
    profile: DonorProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "DONOR":
        raise HTTPException(
            status_code=403,
            detail="Only donor accounts can create donor profiles.",
        )

    existing = db.execute(
        select(donor_profiles.c.id).where(
            donor_profiles.c.user_id == current_user["id"]
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Donor profile already exists.",
        )

    try:
        result = db.execute(
            insert(donor_profiles)
            .values(
                user_id=current_user["id"],
                organization_name=profile.organization_name.strip(),
                donor_type=profile.donor_type.strip(),
                license_number=profile.license_number,
                address=profile.address.strip(),
                city=profile.city.strip(),
                state=profile.state.strip(),
                postal_code=profile.postal_code.strip(),
                latitude=profile.latitude,
                longitude=profile.longitude,
            )
            .returning(donor_profiles)
        )

        new_profile = result.mappings().one()
        db.commit()

        return {
            "message": "Donor profile created successfully.",
            "profile": dict(new_profile),
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A donor profile already exists for this account.",
        )


@router.get("/profile")
def get_donor_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "DONOR":
        raise HTTPException(
            status_code=403,
            detail="Only donors can access this profile.",
        )

    profile = db.execute(
        select(donor_profiles).where(
            donor_profiles.c.user_id == current_user["id"]
        )
    ).mappings().first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Donor profile not found.",
        )

    return dict(profile)
