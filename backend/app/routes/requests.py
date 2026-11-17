
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, select, insert, func, update
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user
from app.core.notifications import create_notification

from app.schemas.request import (
    DonationRequestCreate,
    DonationRequestRespond
)


router = APIRouter(prefix="/requests", tags=["Donation Requests"])

metadata = MetaData()

donations = Table("donations", metadata, autoload_with=engine)
donation_requests = Table(
    "donation_requests", metadata, autoload_with=engine
)
ngo_profiles = Table("ngo_profiles", metadata, autoload_with=engine)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_donation_request(
    data: DonationRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "NGO":
        raise HTTPException(
            status_code=403,
            detail="Only NGO accounts can request donations."
        )

    ngo = db.execute(
        select(ngo_profiles.c.id).where(
            ngo_profiles.c.user_id == current_user["id"]
        )
    ).first()

    if not ngo:
        raise HTTPException(
            status_code=400,
            detail="Create your NGO profile first."
        )

    donation = db.execute(
        select(donations).where(
            donations.c.id == data.donation_id
        )
    ).mappings().first()

    if not donation:
        raise HTTPException(
            status_code=404,
            detail="Donation not found."
        )

    if donation["status"] != "AVAILABLE":
        raise HTTPException(
            status_code=400,
            detail="This donation is not available."
        )

    # Database expires_at is timezone-naive.
    now = datetime.now()

    expiry = donation["expires_at"]

    # Safely compare both datetimes in the same format.
    if expiry.tzinfo is not None:
        expiry = expiry.replace(tzinfo=None)

    if expiry <= now:
        raise HTTPException(
            status_code=400,
            detail="This donation has expired."
        )

    requested_total = db.execute(
        select(
            func.coalesce(
                func.sum(donation_requests.c.requested_quantity), 0
            )
        ).where(
            donation_requests.c.donation_id == data.donation_id,
            donation_requests.c.status.in_(["PENDING", "ACCEPTED"])
        )
    ).scalar_one()

    remaining_quantity = (
        float(donation["quantity"]) - float(requested_total)
    )

    if data.requested_quantity > remaining_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {remaining_quantity} quantity is available."
        )

    result = db.execute(
        insert(donation_requests)
        .values(
            donation_id=data.donation_id,
            ngo_id=current_user["id"],
            requested_quantity=data.requested_quantity,
            message=data.message,
            status="PENDING",
            created_at=now
        )
        .returning(donation_requests)
    )

    new_request = result.mappings().one()

    create_notification(
        db=db,
        user_id=donation["donor_id"],
        title="New Donation Request",
        message=(
            f"An NGO has requested {data.requested_quantity} "
            f"{donation['unit']} of your donation: {donation['title']}."
        ),
        notification_type="DONATION_REQUEST"
    )

    db.commit()

    return {
        "message": "Donation request submitted successfully.",
        "request": dict(new_request)
    }


@router.get("/my")
def get_my_requests(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "NGO":
        raise HTTPException(
            status_code=403,
            detail="Only NGOs can view their requests."
        )

    result = db.execute(
        select(donation_requests)
        .where(donation_requests.c.ngo_id == current_user["id"])
        .order_by(donation_requests.c.created_at.desc())
    ).mappings().all()

    return {
        "total_requests": len(result),
        "requests": [dict(item) for item in result]
    }


@router.get("/incoming")
def get_incoming_requests(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "DONOR":
        raise HTTPException(
            status_code=403,
            detail="Only donors can view incoming requests."
        )

    result = db.execute(
        select(
            donation_requests,
            donations.c.title.label("donation_title"),
            donations.c.quantity.label("donation_quantity"),
            donations.c.unit.label("donation_unit")
        )
        .join(
            donations,
            donation_requests.c.donation_id == donations.c.id
        )
        .where(donations.c.donor_id == current_user["id"])
        .order_by(donation_requests.c.created_at.desc())
    ).mappings().all()

    return {
        "total_requests": len(result),
        "requests": [dict(item) for item in result]
    }


@router.patch("/{request_id}/respond")
def respond_to_request(
    request_id: int,
    data: DonationRequestRespond,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "DONOR":
        raise HTTPException(
            status_code=403,
            detail="Only donors can respond to requests."
        )

    request = db.execute(
        select(
            donation_requests,
            donations.c.donor_id.label("donor_id"),
            donations.c.status.label("donation_status")
        )
        .join(
            donations,
            donation_requests.c.donation_id == donations.c.id
        )
        .where(donation_requests.c.id == request_id)
    ).mappings().first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Donation request not found."
        )

    if request["donor_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You cannot respond to another donor's request."
        )

    if request["status"] != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="This request has already been processed."
        )

    if request["donation_status"] != "AVAILABLE":
        raise HTTPException(
            status_code=400,
            detail="This donation is no longer available."
        )

    now = datetime.now()

    if data.action == "ACCEPT":
        db.execute(
            update(donation_requests)
            .where(donation_requests.c.id == request_id)
            .values(
                status="ACCEPTED",
                responded_at=now
            )
        )

        db.execute(
            update(donations)
            .where(donations.c.id == request["donation_id"])
            .values(
                status="ACCEPTED",
                updated_at=now
            )
        )

        db.execute(
            update(donation_requests)
            .where(
                donation_requests.c.donation_id == request["donation_id"],
                donation_requests.c.status == "PENDING",
                donation_requests.c.id != request_id
            )
            .values(
                status="REJECTED",
                rejection_reason="Donation accepted by another NGO.",
                responded_at=now
            )
        )

        message = "Donation request accepted successfully."

    else:
        if not data.rejection_reason or not data.rejection_reason.strip():
            raise HTTPException(
                status_code=400,
                detail="Please provide a rejection reason."
            )

        db.execute(
            update(donation_requests)
            .where(donation_requests.c.id == request_id)
            .values(
                status="REJECTED",
                rejection_reason=data.rejection_reason.strip(),
                responded_at=now
            )
        )

        message = "Donation request rejected successfully."

    create_notification(
        db=db,
        user_id=request["ngo_id"],
        title=f"Donation Request {data.action.title()}",
        message=(
            f"Your request for donation #{request['donation_id']} "
            f"has been {data.action.lower()}ed by the donor."
        ),
        notification_type="REQUEST_RESPONSE"
    )

    db.commit()

    return {
        "message": message,
        "request_id": request_id,
        "status": (
            "ACCEPTED" if data.action == "ACCEPT" else "REJECTED"
        )
    }
