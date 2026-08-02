"""智能体助手路由：/agent/chat、/agent/confirm、/agent/status、/agent/sessions。"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.services.agent import AgentMessage
from app.services.agent.actions import ActionExecutor
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import IntentResolver
from app.services.agent.llm import OllamaBusy, OllamaClient, OllamaTimeout, OllamaUnavailable
from app.services.agent.session import SessionStore

logger = logging.getLogger("student_management")

agent_llm = OllamaClient(
    base_url=settings.ollama_base_url,
    model=settings.ollama_model,
    timeout=settings.ollama_timeout,
    max_concurrency=settings.ollama_max_concurrency,
    queue_timeout=settings.ollama_queue_timeout,
    circuit_failures=settings.ollama_circuit_failures,
    circuit_cooldown=settings.ollama_circuit_cooldown,
)
resolver = IntentResolver(agent_llm)
session_store = SessionStore(
    ttl=settings.agent_session_ttl,
    max_sessions=settings.agent_session_limit,
)
confirmation_store = ConfirmationStore(ttl=settings.agent_confirm_ttl)
executor = ActionExecutor(agent_llm, confirmation_store, session_store)

router = APIRouter(prefix="/agent", tags=["智能体助手"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class ConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1)


@router.post("/chat", summary="发送消息给智能体")
async def agent_chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user["username"]
    role = current_user["role"]
    if req.session_id:
        if not session_store.get(user_id, req.session_id):
            return {
                "session_id": req.session_id,
                "messages": [AgentMessage(kind="error", content="会话不存在或已过期，请新建对话")],
                "source": "none",
            }
        session_id = req.session_id
    else:
        session_id = session_store.create(user_id)["session_id"]

    session_store.add_message(user_id, session_id, "user", req.message)
    try:
        intents, source = await resolver.resolve(req.message)
    except Exception:
        logger.exception("intent resolution failed")
        intents, source = [], "fallback"

    messages: list[AgentMessage] = []
    success = failed = skipped = 0
    interrupted = False
    for intent in intents:
        try:
            outcome = await executor.execute(intent, user_id, role, session_id, db, raw_text=req.message)
        except (OllamaBusy, OllamaUnavailable) as exc:
            failed += 1
            interrupted = True
            messages.append(AgentMessage(kind="error", content=str(exc)))
            break
        except OllamaTimeout:
            failed += 1
            interrupted = True
            messages.append(AgentMessage(kind="error", content="模型响应超时，请稍后再试"))
            break
        except Exception:
            logger.exception("agent action failed")
            failed += 1
            interrupted = True
            messages.append(AgentMessage(kind="error", content="系统异常，请稍后重试"))
            break
        if not outcome:
            skipped += 1
            continue
        messages.extend(outcome)
        if any(m.kind == "error" for m in outcome):
            failed += 1
        else:
            success += 1

    summary = AgentMessage(
        kind="summary",
        content=f"共 {len(intents)} 个指令：成功 {success}、业务失败 {failed}、跳过 {skipped}、系统中断 {1 if interrupted else 0}",
    )
    messages.append(summary)
    for m in messages:
        session_store.add_message(user_id, session_id, "assistant", m.content or m.title, kind=m.kind)
    return {"session_id": session_id, "messages": messages, "source": source}


@router.post("/confirm", summary="确认执行写操作")
async def agent_confirm(
    req: ConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = confirmation_store.consume(current_user["username"], req.token)
    messages = await executor.execute_confirm(payload, db)
    return {"messages": messages}


@router.get("/status", summary="智能体与模型状态")
async def agent_status(current_user: dict = Depends(get_current_user)):
    return {
        "ollama": agent_llm.status(),
        "session_count": len(session_store.list_sessions(current_user["username"])),
    }


@router.get("/sessions", summary="会话列表")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    return {"sessions": session_store.list_sessions(current_user["username"])}


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    if not session_store.delete(current_user["username"], session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "已删除"}
