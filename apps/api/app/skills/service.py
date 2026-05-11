import logging

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.skills.catalog import BUILTIN_SKILLS
from app.skills.models import Skill, UserSkill
from app.skills.schemas import SkillCreate, SkillUpdate
from app.shared.errors import AppError

logger = logging.getLogger(__name__)


def seed_builtin_skills(db: Session) -> None:
    for entry in BUILTIN_SKILLS:
        existing = db.query(Skill).filter(Skill.skill_id == entry["skill_id"]).first()
        if existing is not None:
            continue
        skill = Skill(
            skill_id=entry["skill_id"],
            name=entry["name"],
            description=entry.get("description"),
            category=entry.get("category"),
            prompt_template=entry.get("prompt_template"),
            mock_tool_name=entry.get("mock_tool_name"),
            visibility="shared",
            source="system",
        )
        db.add(skill)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.debug("Concurrent skill seed conflict; skipping")


def list_skills_with_install_state(db: Session, user_id: str) -> list[dict]:
    skills = db.query(Skill).filter(
        or_(
            Skill.source == "system",
            Skill.visibility == "shared",
            Skill.owner_user_id == user_id,
        )
    ).all()
    installed_skill_ids = {
        us.skill_id
        for us in db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
    }

    result = []
    for skill in skills:
        result.append({
            "id": skill.id,
            "skill_id": skill.skill_id,
            "name": skill.name,
            "description": skill.description,
            "category": skill.category,
            "prompt_template": skill.prompt_template,
            "mock_tool_name": skill.mock_tool_name,
            "owner_user_id": skill.owner_user_id,
            "visibility": skill.visibility,
            "source": skill.source,
            "installed": skill.id in installed_skill_ids,
        })
    return result


def _ensure_can_manage(skill: Skill, user_id: str, role: str) -> None:
    if skill.source == "system":
        raise AppError(code="SYSTEM_SKILL_IMMUTABLE", message="System skills cannot be modified.", status_code=400)
    if skill.owner_user_id != user_id and role != "admin":
        raise AppError(code="FORBIDDEN", message="Cannot manage another user's skill.", status_code=403)


def _ensure_visibility_allowed(visibility: str, role: str) -> None:
    if visibility == "shared" and role != "admin":
        raise AppError(code="FORBIDDEN", message="Only admins can publish shared skills.", status_code=403)


def create_skill(db: Session, user_id: str, role: str, payload: SkillCreate) -> dict:
    _ensure_visibility_allowed(payload.visibility, role)
    existing = db.query(Skill).filter(Skill.skill_id == payload.skill_id).first()
    if existing is not None:
        raise AppError(code="SKILL_EXISTS", message="Skill id already exists.", status_code=409)

    skill = Skill(
        skill_id=payload.skill_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        prompt_template=payload.prompt_template,
        mock_tool_name=payload.mock_tool_name,
        owner_user_id=user_id,
        visibility=payload.visibility,
        source="user",
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill, installed=False)


def update_skill(db: Session, user_id: str, role: str, builtin_skill_id: str, payload: SkillUpdate) -> dict | None:
    skill = db.query(Skill).filter(Skill.skill_id == builtin_skill_id).first()
    if skill is None:
        return None
    _ensure_can_manage(skill, user_id, role)
    if payload.visibility is not None:
        _ensure_visibility_allowed(payload.visibility, role)

    for field in ("name", "description", "category", "prompt_template", "mock_tool_name", "visibility"):
        value = getattr(payload, field)
        if value is not None:
            setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    installed = db.query(UserSkill).filter(UserSkill.user_id == user_id, UserSkill.skill_id == skill.id).first() is not None
    return _skill_to_dict(skill, installed=installed)


def delete_skill(db: Session, user_id: str, role: str, builtin_skill_id: str) -> bool | None:
    skill = db.query(Skill).filter(Skill.skill_id == builtin_skill_id).first()
    if skill is None:
        return None
    _ensure_can_manage(skill, user_id, role)
    db.query(UserSkill).filter(UserSkill.skill_id == skill.id).delete()
    db.delete(skill)
    db.commit()
    return True


def _skill_to_dict(skill: Skill, installed: bool) -> dict:
    return {
        "id": skill.id,
        "skill_id": skill.skill_id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "prompt_template": skill.prompt_template,
        "mock_tool_name": skill.mock_tool_name,
        "owner_user_id": skill.owner_user_id,
        "visibility": skill.visibility,
        "source": skill.source,
        "installed": installed,
    }


def install_skill_for_user(db: Session, user_id: str, builtin_skill_id: str) -> dict | None:
    skill = db.query(Skill).filter(
        Skill.skill_id == builtin_skill_id,
        or_(Skill.source == "system", Skill.visibility == "shared", Skill.owner_user_id == user_id),
    ).first()
    if skill is None:
        return None

    existing = db.query(UserSkill).filter(
        UserSkill.user_id == user_id,
        UserSkill.skill_id == skill.id,
    ).first()

    if existing is None:
        user_skill = UserSkill(user_id=user_id, skill_id=skill.id)
        db.add(user_skill)
        db.commit()

    return {"skill_id": builtin_skill_id, "installed": True}


def uninstall_skill_for_user(db: Session, user_id: str, builtin_skill_id: str) -> dict | None:
    skill = db.query(Skill).filter(
        Skill.skill_id == builtin_skill_id,
        or_(Skill.source == "system", Skill.visibility == "shared", Skill.owner_user_id == user_id),
    ).first()
    if skill is None:
        return None

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user_id,
        UserSkill.skill_id == skill.id,
    ).first()

    if user_skill is not None:
        db.delete(user_skill)
        db.commit()

    return {"skill_id": builtin_skill_id, "installed": False}
