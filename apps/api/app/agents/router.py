import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.agents.graph import AgentContext, execute_graph
from app.agents.models import AgentRun
from app.agents.schemas import RunCreate, RunResponse
from app.agents.service import create_run, recover_stale_runs, resolve_chat_adapter
from app.agents.stream import RunEvent, create_queue, get_history, get_queue, cleanup, emit
from app.auth.models import User
from app.shared.auth import ALGORITHM, get_current_user
from app.shared.config import Settings, get_settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent/runs", tags=["agent_runs"])


def _get_user_id_from_token(token: str | None, db: Session, settings: Settings) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Missing token query parameter")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user.id


@router.post("", response_model=RunResponse, status_code=200)
def create_agent_run(
    body: RunCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    model_adapter = resolve_chat_adapter(body.model_provider_id, settings)

    run = create_run(
        db=db,
        user_id=current_user.id,
        skill_id=body.skill_id,
        user_message=body.user_message,
        conversation_id=body.conversation_id,
        model_provider_id=body.model_provider_id,
    )

    create_queue(run.id)

    ctx = AgentContext(
        run_id=run.id,
        user_id=run.user_id,
        conversation_id=run.conversation_id,
        skill_id=body.skill_id,
        model_provider_id=body.model_provider_id,
        user_message=body.user_message,
        model_adapter=model_adapter,
    )

    background_tasks.add_task(_execute_run_background, ctx)

    return RunResponse(
        id=run.id,
        conversation_id=run.conversation_id,
        user_id=run.user_id,
        skill_id=run.skill_id,
        model_provider_id=run.model_provider_id,
        status=run.status,
        structured_output=run.structured_output,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _execute_run_background(ctx: AgentContext):
    from app.shared.database import get_session_factory

    factory = get_session_factory()
    if factory is None:
        logger.error("Database not initialized for background task")
        emit(ctx.run_id, RunEvent(event_type="stream_closed", data={"run_id": ctx.run_id}))
        return

    db = factory()
    try:
        execute_graph(ctx, db)
    except Exception:
        logger.exception("Agent run %s failed in background", ctx.run_id)
    finally:
        db.close()
        emit(ctx.run_id, RunEvent(event_type="stream_closed", data={"run_id": ctx.run_id}))


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recover_stale_runs(db)

    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return RunResponse(
        id=run.id,
        conversation_id=run.conversation_id,
        user_id=run.user_id,
        skill_id=run.skill_id,
        model_provider_id=run.model_provider_id,
        status=run.status,
        structured_output=run.structured_output,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.get("/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_id = _get_user_id_from_token(token, db, settings)

    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        try:
            sent_keys = set()
            for event in get_history(run_id):
                key = (event.event_type, event.timestamp.isoformat(), id(event))
                if key not in sent_keys:
                    sent_keys.add(key)
                    yield f"event: {event.event_type}\ndata: {json.dumps(event.data)}\n\n"

            q = get_queue(run_id)
            if q:
                import asyncio
                while True:
                    try:
                        if await request.is_disconnected():
                            break
                        event = await asyncio.wait_for(q.get(), timeout=30.0)
                        key = (event.event_type, event.timestamp.isoformat(), id(event))
                        if key not in sent_keys:
                            sent_keys.add(key)
                            yield f"event: {event.event_type}\ndata: {json.dumps(event.data)}\n\n"
                        if event.event_type in ("run_completed", "run_failed", "stream_closed"):
                            break
                    except asyncio.TimeoutError:
                        break
        finally:
            cleanup(run_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
