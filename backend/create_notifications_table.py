
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    func,
    Index,
)

from app.core.database import engine

metadata = MetaData()

users = Table(
    "users",
    metadata,
    autoload_with=engine,
)

notifications = Table(
    "notifications",
    metadata,

    Column(
        "id",
        BigInteger,
        primary_key=True,
        autoincrement=True,
    ),

    Column(
        "user_id",
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),

    Column("title", String(200), nullable=False),

    Column("message", Text, nullable=False),

    Column(
        "notification_type",
        String(50),
        nullable=False,
    ),

    Column(
        "is_read",
        Boolean,
        nullable=False,
        server_default="false",
    ),

    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

Index("ix_notifications_user_id", notifications.c.user_id)

metadata.create_all(
    engine,
    tables=[notifications],
    checkfirst=True,
)

print("Notifications table created successfully!")
