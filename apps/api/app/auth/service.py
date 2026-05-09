from sqlalchemy.orm import Session

from app.auth.models import User
from app.shared.auth import create_access_token, hash_password, verify_password
from app.shared.config import Settings

_DUMMY_HASH = hash_password("dummy-password-that-will-never-match")


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_login_token(user: User, settings: Settings) -> dict:
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        settings=settings,
    )
    return {"access_token": token, "token_type": "bearer"}
