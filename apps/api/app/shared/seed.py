from sqlalchemy.orm import Session

from app.auth.models import User
from app.shared.auth import hash_password

_SEED_USERS = [
    {"email": "hrbp@example.com", "password": "password123", "role": "hrbp", "display_name": "HRBP User"},
    {"email": "admin@example.com", "password": "password123", "role": "admin", "display_name": "Admin User"},
]


def seed_local_users(db: Session) -> None:
    for entry in _SEED_USERS:
        existing = db.query(User).filter(User.email == entry["email"]).first()
        if existing is not None:
            continue
        user = User(
            email=entry["email"],
            hashed_password=hash_password(entry["password"]),
            role=entry["role"],
            display_name=entry["display_name"],
        )
        db.add(user)
    db.commit()
