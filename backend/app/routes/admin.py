
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, Table, MetaData, func
from sqlalchemy.orm import Session

from app.core.database import get_db, engine
from app.core.dependencies import get_current_admin
from app.core.notifications import create_notification
from app.routes.auth import users

metadata = MetaData()

ngo_profiles = Table(
    "ngo_profiles",
    metadata,
    autoload_with=engine,
)

donations = Table(
    "donations",
    metadata,
    autoload_with=engine,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# VIEW PENDING USERS

@router.get("/pending-users")
def get_pending_users(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    pending_users = db.execute(
        select(
            users.c.id,
            users.c.full_name,
            users.c.email,
            users.c.phone,
            users.c.role,
            users.c.created_at,
        )
        .where(users.c.is_active.is_(False))
        .order_by(users.c.created_at.asc())
    ).mappings().all()

    return {
        "total": len(pending_users),
        "users": [dict(user) for user in pending_users],
    }


# APPROVE USER

@router.patch("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    target_user = db.execute(
        select(users).where(users.c.id == user_id)
    ).mappings().first()

    if not target_user:
        raise HTTPException(404, "User not found.")

    if target_user["is_active"]:
        raise HTTPException(400, "User is already active.")

    db.execute(
        update(users)
        .where(users.c.id == user_id)
        .values(
            is_active=True,
            is_verified=True,
        )
    )

    create_notification(
        db=db,
        user_id=user_id,
        title="Account Approved",
        message="Your FoodBridge account has been approved. You can now log in.",
        notification_type="ACCOUNT_APPROVAL"
    )

    db.commit()

    return {
        "message": "User approved successfully.",
        "user_id": user_id,
        "email": target_user["email"],
        "account_status": "APPROVED",
    }


# REJECT USER

@router.patch("/users/{user_id}/reject")
def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    target_user = db.execute(
        select(users).where(users.c.id == user_id)
    ).mappings().first()

    if not target_user:
        raise HTTPException(404, "User not found.")

    if target_user["is_active"]:
        raise HTTPException(
            400,
            "Active users cannot be rejected through this endpoint."
        )

    # Notify before deleting the pending account
    create_notification(
        db=db,
        user_id=user_id,
        title="Registration Rejected",
        message="Your FoodBridge registration was not approved.",
        notification_type="ACCOUNT_REJECTION"
    )

    db.commit()

    # Existing behavior: delete rejected pending user
    db.execute(
        users.delete().where(users.c.id == user_id)
    )

    db.commit()

    return {
        "message": "Registration rejected.",
        "user_id": user_id,
    }


# VIEW PENDING NGO PROFILES

@router.get("/pending-ngos")
def get_pending_ngos(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    pending_ngos = db.execute(
        select(
            ngo_profiles,
            users.c.full_name,
            users.c.email,
            users.c.phone,
        )
        .join(users, ngo_profiles.c.user_id == users.c.id)
        .where(ngo_profiles.c.verification_status == "PENDING")
        .order_by(ngo_profiles.c.id.asc())
    ).mappings().all()

    return {
        "total": len(pending_ngos),
        "ngos": [dict(ngo) for ngo in pending_ngos],
    }


# APPROVE NGO PROFILE

@router.patch("/ngos/{ngo_id}/approve")
def approve_ngo(
    ngo_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    ngo = db.execute(
        select(ngo_profiles).where(ngo_profiles.c.id == ngo_id)
    ).mappings().first()

    if not ngo:
        raise HTTPException(404, "NGO profile not found.")

    if ngo["verification_status"] != "PENDING":
        raise HTTPException(
            400,
            "NGO profile is not pending verification."
        )

    db.execute(
        update(ngo_profiles)
        .where(ngo_profiles.c.id == ngo_id)
        .values(verification_status="APPROVED")
    )

    create_notification(
        db=db,
        user_id=ngo["user_id"],
        title="NGO Verification Approved",
        message="Your NGO profile has been verified successfully by FoodBridge admin.",
        notification_type="NGO_APPROVAL"
    )

    db.commit()

    return {
        "message": "NGO profile approved successfully.",
        "ngo_id": ngo_id,
        "verification_status": "APPROVED",
    }


# REJECT NGO PROFILE

@router.patch("/ngos/{ngo_id}/reject")
def reject_ngo(
    ngo_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    ngo = db.execute(
        select(ngo_profiles).where(ngo_profiles.c.id == ngo_id)
    ).mappings().first()

    if not ngo:
        raise HTTPException(404, "NGO profile not found.")

    if ngo["verification_status"] != "PENDING":
        raise HTTPException(
            400,
            "NGO profile is not pending verification."
        )

    db.execute(
        update(ngo_profiles)
        .where(ngo_profiles.c.id == ngo_id)
        .values(verification_status="REJECTED")
    )

    create_notification(
        db=db,
        user_id=ngo["user_id"],
        title="NGO Verification Rejected",
        message="Your NGO profile verification was rejected. Please contact FoodBridge admin for further details.",
        notification_type="NGO_REJECTION"
    )

    db.commit()

    return {
        "message": "NGO profile rejected.",
        "ngo_id": ngo_id,
        "verification_status": "REJECTED",
    }


# ADMIN DASHBOARD STATISTICS

@router.get("/dashboard")
def get_admin_dashboard(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    total_users = db.execute(
        select(func.count()).select_from(users)
    ).scalar() or 0

    total_donors = db.execute(
        select(func.count()).select_from(users)
        .where(users.c.role == "DONOR")
    ).scalar() or 0

    total_ngos = db.execute(
        select(func.count()).select_from(users)
        .where(users.c.role == "NGO")
    ).scalar() or 0

    total_volunteers = db.execute(
        select(func.count()).select_from(users)
        .where(users.c.role == "VOLUNTEER")
    ).scalar() or 0

    pending_users = db.execute(
        select(func.count()).select_from(users)
        .where(users.c.is_active.is_(False))
    ).scalar() or 0

    total_ngo_profiles = db.execute(
        select(func.count()).select_from(ngo_profiles)
    ).scalar() or 0

    pending_ngos = db.execute(
        select(func.count()).select_from(ngo_profiles)
        .where(ngo_profiles.c.verification_status == "PENDING")
    ).scalar() or 0

    total_donations = db.execute(
        select(func.count()).select_from(donations)
    ).scalar() or 0

    available_donations = db.execute(
        select(func.count()).select_from(donations)
        .where(donations.c.status == "AVAILABLE")
    ).scalar() or 0

    delivered_donations = db.execute(
        select(func.count()).select_from(donations)
        .where(donations.c.status == "DELIVERED")
    ).scalar() or 0

    collected_donations = db.execute(
        select(func.count()).select_from(donations)
        .where(donations.c.status == "COLLECTED")
    ).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "donors": total_donors,
            "ngos": total_ngos,
            "volunteers": total_volunteers,
            "pending_approvals": pending_users,
        },
        "ngos": {
            "total_profiles": total_ngo_profiles,
            "pending_verifications": pending_ngos,
        },
        "donations": {
            "total": total_donations,
            "available": available_donations,
            "collected": collected_donations,
            "delivered": delivered_donations,
        },
    }
