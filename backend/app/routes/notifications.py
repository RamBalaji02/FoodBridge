
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import MetaData, Table, select, update, delete, func
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

metadata = MetaData()

users = Table(
    "users",
    metadata,
    autoload_with=engine,
)

notifications = Table(
    "notifications",
    metadata,
    autoload_with=engine,
)


# --------------------------------------------------
# VIEW MY NOTIFICATIONS
# --------------------------------------------------

@router.get("/my")
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]

    result = db.execute(
        select(notifications)
        .where(notifications.c.user_id == user_id)
        .order_by(notifications.c.created_at.desc())
    ).mappings().all()

    unread_count = db.execute(
        select(func.count())
        .select_from(notifications)
        .where(
            notifications.c.user_id == user_id,
            notifications.c.is_read.is_(False),
        )
    ).scalar() or 0

    return {
        "total": len(result),
        "unread_count": unread_count,
        "notifications": [dict(item) for item in result],
    }


# --------------------------------------------------
# MARK ONE NOTIFICATION AS READ
# --------------------------------------------------

@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]

    result = db.execute(
        update(notifications)
        .where(
            notifications.c.id == notification_id,
            notifications.c.user_id == user_id,
        )
        .values(is_read=True)
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    db.commit()

    return {
        "message": "Notification marked as read.",
        "notification_id": notification_id,
    }


# --------------------------------------------------
# MARK ALL NOTIFICATIONS AS READ
# --------------------------------------------------

@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]

    db.execute(
        update(notifications)
        .where(
            notifications.c.user_id == user_id,
            notifications.c.is_read.is_(False),
        )
        .values(is_read=True)
    )

    db.commit()

    return {
        "message": "All notifications marked as read.",
    }


# --------------------------------------------------
# DELETE ONE NOTIFICATION
# --------------------------------------------------

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]

    result = db.execute(
        delete(notifications).where(
            notifications.c.id == notification_id,
            notifications.c.user_id == user_id,
        )
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    db.commit()

    return {
        "message": "Notification deleted successfully.",
        "notification_id": notification_id,
    }
