from sqlalchemy import MetaData, Table, insert

from app.core.database import engine

metadata = MetaData()

notifications = Table(
    "notifications",
    metadata,
    autoload_with=engine
)


def create_notification(
    db,
    user_id: int,
    title: str,
    message: str,
    notification_type: str
):
    db.execute(
        insert(notifications).values(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
    )