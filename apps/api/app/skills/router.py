from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.shared.auth import get_current_user
from app.shared.database import get_db
from app.skills.schemas import InstallResponse, SkillResponse
from app.skills.service import install_skill_for_user, list_skills_with_install_state, uninstall_skill_for_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
def list_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_skills_with_install_state(db, current_user.id)


@router.post("/{skill_id}/install", response_model=InstallResponse)
def install_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = install_skill_for_user(db, current_user.id, skill_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return result


@router.delete("/{skill_id}/install", response_model=InstallResponse)
def uninstall_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = uninstall_skill_for_user(db, current_user.id, skill_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return result
