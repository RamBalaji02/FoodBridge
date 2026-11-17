
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import MetaData, Table, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# Connect to the existing PostgreSQL users table.
metadata = MetaData()

users = Table(
    "users",
    metadata,
    autoload_with=engine,
)


# --------------------------------------------------
# REGISTER API
# --------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = user.email.lower().strip()

    # Check duplicate email.
    existing_user = db.execute(
        select(users.c.id).where(users.c.email == email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    now = datetime.now(timezone.utc)

    try:
        statement = (
            insert(users)
            .values(
                full_name=user.full_name.strip(),
                email=email,
                phone=user.phone.strip(),
                hashed_password=hash_password(user.password),
                role=user.role,
                is_active=False,
                is_verified=False,
                created_at=now,
                updated_at=now,
            )
            .returning(users.c.id)
        )

        result = db.execute(statement)
        new_user_id = result.scalar_one()

        db.commit()

        return RegisterResponse(
            message="Registration successful. Waiting for admin approval.",
            user_id=new_user_id,
            email=email,
            role=user.role,
            account_status="PENDING",
        )

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# LOGIN API
# --------------------------------------------------

@router.post(
    "/login",
    response_model=LoginResponse,
)
def login_user(
    user: LoginRequest,
    db: Session = Depends(get_db),
):
    email = user.email.lower().strip()

    # Find user using email.
    existing_user = db.execute(
        select(users).where(users.c.email == email)
    ).mappings().first()

    # Check whether user exists.
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Verify password.
    password_valid = verify_password(
        user.password,
        existing_user["hashed_password"],
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Check admin approval.
    if not existing_user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is waiting for admin approval.",
        )

    # Generate JWT access token.
    access_token = create_access_token(
        user_id=existing_user["id"],
        role=existing_user["role"],
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=existing_user["id"],
        email=existing_user["email"],
        role=existing_user["role"],
    )
