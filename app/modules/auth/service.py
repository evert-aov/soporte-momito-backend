from sqlalchemy.orm import Session
from app.modules.users.repository import UserRepository, RoleRepository
from app.core.security import verify_password, create_access_token, get_password_hash
from fastapi import HTTPException, status


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def login(self, email: str, password: str) -> str:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return create_access_token({"sub": user.email})

    def register(self, full_name: str, email: str, password: str):
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        role_repo = RoleRepository(self.db)
        cliente_role = next(
            (r for r in role_repo.get_all() if r.name.upper() == "CLIENTE"), None
        )
        return self.user_repo.create(
            full_name=full_name,
            email=email,
            password_hash=get_password_hash(password),
            role_id=cliente_role.id if cliente_role else None,
        )
