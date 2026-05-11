from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.models import User
from app.shared.auth import get_current_user
from app.shared.database import get_db
from app.skills.schemas import InstallResponse, SkillCreate, SkillResponse, SkillUpdate
from app.skills.service import (
    create_skill,
    delete_skill,
    install_skill_for_user,
    list_skills_with_install_state,
    uninstall_skill_for_user,
    update_skill,
)

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
def list_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_skills_with_install_state(db, current_user.id)


@router.post("", response_model=SkillResponse)
def create_custom_skill(
    body: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_skill(db, current_user.id, current_user.role, body)


@router.patch("/{skill_id}", response_model=SkillResponse)
def update_custom_skill(
    skill_id: str,
    body: SkillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_skill(db, current_user.id, current_user.role, skill_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return result


@router.delete("/{skill_id}", status_code=204)
def delete_custom_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = delete_skill(db, current_user.id, current_user.role, skill_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return Response(status_code=204)


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
