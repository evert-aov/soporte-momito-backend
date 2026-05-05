from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from fastapi import Request
from jose import JWTError
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from app.core.security import decode_token
from app.modules.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = repo.get_by_email(email)
    if user is None:
        raise credentials_exception
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[object]:
    """Returns user if token is present and valid, otherwise None (guest)."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, token = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            return None
        repo = UserRepository(db)
        return repo.get_by_email(email)
    except JWTError:
        return None


_ADMIN_ROLES = {"super_admin"}
_SELLER_ROLES = {"vendedor"} | _ADMIN_ROLES


def _role(user) -> str:
    return (getattr(user.role, "name", "") or "").strip().lower() if user.role else ""


def require_superadmin(current_user=Depends(get_current_user)):
    if _role(current_user) not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    return current_user


def require_admin(current_user=Depends(get_current_user)):
    if _role(current_user) not in _ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_seller(current_user=Depends(get_current_user)):
    if _role(current_user) not in _SELLER_ROLES:
        raise HTTPException(status_code=403, detail="Seller access required")
    return current_user


def is_admin(user) -> bool:
    return _role(user) in _ADMIN_ROLES


def is_seller_or_above(user) -> bool:
    return _role(user) in _SELLER_ROLES
