import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.skills.catalog import BUILTIN_SKILLS
from app.skills.models import Skill, UserSkill

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
        )
        db.add(skill)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.debug("Concurrent skill seed conflict; skipping")


def list_skills_with_install_state(db: Session, user_id: str) -> list[dict]:
    skills = db.query(Skill).all()
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
            "installed": skill.id in installed_skill_ids,
        })
    return result


def install_skill_for_user(db: Session, user_id: str, builtin_skill_id: str) -> dict | None:
    skill = db.query(Skill).filter(Skill.skill_id == builtin_skill_id).first()
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
    skill = db.query(Skill).filter(Skill.skill_id == builtin_skill_id).first()
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
