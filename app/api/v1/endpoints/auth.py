from datetime import timedelta, timezone, datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, blacklist_token, get_current_user,
)
from app.core.config import settings
from app.services.user_service import UserService
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, data: UserRegister, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    if await service.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await service.create_user(data)
    await db.commit()
    await db.refresh(user)

    # Fire verification email in background
    try:
        from app.tasks.email_tasks import send_verification_email
        send_verification_email.delay(str(user.id), user.email)
    except Exception:
        pass  # don't fail registration if email task fails

    payload = {"sub": str(user.id), "role": user.role}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer",
        "user": user,
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.get_user_by_email(data.email)

    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    payload = {"sub": str(user.id), "role": user.role}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    from app.core.security import is_token_blacklisted
    if await is_token_blacklisted(payload.get("jti", "")):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    service = UserService(db)
    user = await service.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    new_payload = {"sub": str(user.id), "role": user.role}
    return {
        "access_token": create_access_token(new_payload),
        "token_type": "bearer",
    }


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    current_user=Depends(get_current_user),
):
    # Get JTI from Authorization header token
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    payload = decode_token(token)
    if payload and payload.get("jti"):
        expire_secs = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await blacklist_token(payload["jti"], expire_secs)


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me")
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = UserService(db)
    user = await service.update_user(current_user.id, data.model_dump(exclude_unset=True))
    await db.commit()
    return user


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, email: str, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.get_user_by_email(email)
    if user:
        try:
            from app.tasks.email_tasks import send_password_reset_email
            from app.utils.helpers import generate_reset_token
            token = generate_reset_token(str(user.id))
            send_password_reset_email.delay(email, token)
        except Exception:
            pass
    # Always return 200 to prevent email enumeration
    return {"message": "If this email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    from app.utils.helpers import verify_reset_token
    user_id = verify_reset_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    from app.core.security import get_password_hash
    service = UserService(db)
    await service.update_user(user_id, {"hashed_password": get_password_hash(new_password)})
    await db.commit()
    return {"message": "Password updated successfully"}
