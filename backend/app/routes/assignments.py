
from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, select, insert, update
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user
from app.core.notifications import create_notification

from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentStatusUpdate
)

router = APIRouter(
    prefix="/assignments",
    tags=["Pickup Assignments"]
)

metadata = MetaData()

assignments = Table(
    "pickup_assignments", metadata, autoload_with=engine
)
requests = Table(
    "donation_requests", metadata, autoload_with=engine
)
donations = Table(
    "donations", metadata, autoload_with=engine
)
volunteer_profiles = Table(
    "volunteer_profiles", metadata, autoload_with=engine
)


@router.post("/assign", status_code=status.HTTP_201_CREATED)
def assign_volunteer(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "ADMIN":
        raise HTTPException(403, "Only admins can assign volunteers.")

    request = db.execute(
        select(requests).where(requests.c.id == data.request_id)
    ).mappings().first()

    if not request:
        raise HTTPException(404, "Donation request not found.")

    if request["status"] != "ACCEPTED":
        raise HTTPException(400, "Only accepted requests can be assigned.")

    donation = db.execute(
        select(donations).where(
            donations.c.id == request["donation_id"]
        )
    ).mappings().first()

    if not donation or donation["status"] != "ACCEPTED":
        raise HTTPException(400, "Donation is not ready for assignment.")

    existing = db.execute(
        select(assignments.c.id).where(
            assignments.c.request_id == data.request_id
        )
    ).first()

    if existing:
        raise HTTPException(409, "This request already has an assignment.")

    volunteer = db.execute(
        select(volunteer_profiles).where(
            volunteer_profiles.c.user_id == data.volunteer_id
        )
    ).mappings().first()

    if not volunteer:
        raise HTTPException(404, "Volunteer profile not found.")

    if not volunteer["is_available"]:
        raise HTTPException(400, "Volunteer is not available.")

    pickup_otp = str(secrets.randbelow(900000) + 100000)
    delivery_otp = str(secrets.randbelow(900000) + 100000)

    result = db.execute(
        insert(assignments)
        .values(
            donation_id=request["donation_id"],
            request_id=data.request_id,
            volunteer_id=data.volunteer_id,
            status="ASSIGNED",
            pickup_otp=pickup_otp,
            delivery_otp=delivery_otp,
            created_at=datetime.now()
        )
        .returning(assignments)
    )

    assignment = result.mappings().one()

    db.execute(
        update(volunteer_profiles)
        .where(volunteer_profiles.c.user_id == data.volunteer_id)
        .values(is_available=False)
    )

    # Notify volunteer about new assignment
    create_notification(
        db=db,
        user_id=data.volunteer_id,
        title="New Pickup Assignment",
        message=(
            f"You have been assigned to collect and deliver "
            f"the donation: {donation['title']}."
        ),
        notification_type="ASSIGNMENT"
    )

    db.commit()

    return {
        "message": "Volunteer assigned successfully.",
        "assignment": dict(assignment),
        "otp_note": (
            "For this development version, share the pickup OTP "
            "with the donor and delivery OTP with the NGO securely."
        )
    }


@router.get("/my")
def get_my_assignments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "VOLUNTEER":
        raise HTTPException(403, "Only volunteers can view assignments.")

    result = db.execute(
        select(
            assignments.c.id,
            assignments.c.donation_id,
            assignments.c.request_id,
            assignments.c.status,
            assignments.c.pickup_photo_url,
            assignments.c.delivery_photo_url,
            assignments.c.picked_up_at,
            assignments.c.delivered_at,
            assignments.c.notes,
            donations.c.title.label("donation_title"),
            donations.c.pickup_address,
            donations.c.pickup_city
        )
        .join(
            donations,
            assignments.c.donation_id == donations.c.id
        )
        .where(assignments.c.volunteer_id == current_user["id"])
        .order_by(assignments.c.created_at.desc())
    ).mappings().all()

    return {
        "total_assignments": len(result),
        "assignments": [dict(item) for item in result]
    }


@router.patch("/{assignment_id}/status")
def update_assignment_status(
    assignment_id: int,
    data: AssignmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "VOLUNTEER":
        raise HTTPException(403, "Only volunteers can update assignments.")

    assignment = db.execute(
        select(assignments).where(
            assignments.c.id == assignment_id
        )
    ).mappings().first()

    if not assignment:
        raise HTTPException(404, "Assignment not found.")

    if assignment["volunteer_id"] != current_user["id"]:
        raise HTTPException(403, "This assignment belongs to another volunteer.")

    current_status = assignment["status"]
    now = datetime.now()
    values = {}

    if data.action == "ACCEPT":
        if current_status != "ASSIGNED":
            raise HTTPException(400, "Assignment cannot be accepted now.")
        values["status"] = "ACCEPTED"

    elif data.action == "PICKUP":
        if current_status != "ACCEPTED":
            raise HTTPException(400, "Accept the assignment before pickup.")
        if data.otp != assignment["pickup_otp"]:
            raise HTTPException(400, "Invalid pickup OTP.")

        values["status"] = "COLLECTED"
        values["picked_up_at"] = now

        db.execute(
            update(donations)
            .where(donations.c.id == assignment["donation_id"])
            .values(status="COLLECTED", updated_at=now)
        )

    elif data.action == "IN_TRANSIT":
        if current_status != "COLLECTED":
            raise HTTPException(400, "Food must be collected first.")
        values["status"] = "IN_TRANSIT"

    elif data.action == "DELIVER":
        if current_status != "IN_TRANSIT":
            raise HTTPException(400, "Food must be in transit before delivery.")
        if data.otp != assignment["delivery_otp"]:
            raise HTTPException(400, "Invalid delivery OTP.")

        values["status"] = "DELIVERED"
        values["delivered_at"] = now

        db.execute(
            update(donations)
            .where(donations.c.id == assignment["donation_id"])
            .values(status="DELIVERED", updated_at=now)
        )

        db.execute(
            update(volunteer_profiles)
            .where(volunteer_profiles.c.user_id == current_user["id"])
            .values(is_available=True)
        )

        # Get donor and NGO IDs for delivery notifications
        delivery_info = db.execute(
            select(
                donations.c.donor_id,
                requests.c.ngo_id,
                donations.c.title
            )
            .join(
                requests,
                requests.c.id == assignment["request_id"]
            )
            .where(
                donations.c.id == assignment["donation_id"]
            )
        ).mappings().first()

        if delivery_info:
            # Notify donor
            create_notification(
                db=db,
                user_id=delivery_info["donor_id"],
                title="Food Donation Delivered",
                message=(
                    f"Your donation '{delivery_info['title']}' "
                    "has been successfully delivered."
                ),
                notification_type="DELIVERY"
            )

            # Notify NGO
            create_notification(
                db=db,
                user_id=delivery_info["ngo_id"],
                title="Food Donation Delivered",
                message=(
                    f"The requested donation '{delivery_info['title']}' "
                    "has been successfully delivered."
                ),
                notification_type="DELIVERY"
            )

    if data.notes:
        values["notes"] = data.notes

    db.execute(
        update(assignments)
        .where(assignments.c.id == assignment_id)
        .values(**values)
    )

    db.commit()

    return {
        "message": "Assignment status updated successfully.",
        "assignment_id": assignment_id,
        "status": values["status"]
    }
