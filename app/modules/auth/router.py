from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from app.modules.auth.schemas import LoginRequest, TokenResponse, RegisterRequest
from app.modules.auth.service import AuthService
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login con JSON — para el frontend Angular."""
    service = AuthService(db)
    token = service.login(request.email, request.password)
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login con form-data — para el botón Authorize de Swagger."""
    service = AuthService(db)
    token = service.login(form_data.username, form_data.password)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.register(request.full_name, request.email, request.password)
    token = service.login(request.email, request.password)
    return TokenResponse(access_token=token)


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    role_name = current_user.role.name if current_user.role else None
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": role_name,
    }
