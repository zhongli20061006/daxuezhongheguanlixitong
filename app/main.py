"""
FastAPI 应用入口
使用 lifespan 管理应用生命周期（替代已废弃的 @app.on_event）
增加 WebSocket 支持、APScheduler 定时任务、事件总线通知
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from slowapi.errors import RateLimitExceeded
from app.database import async_engine, Base, AsyncSessionLocal
from app.config import settings
from app.limiter import limiter
from app.middleware.error_handler import RequestIdMiddleware, global_exception_handler
from app.utils.logger import setup_logging

# 初始化日志（在应用启动前执行一次）
setup_logging()
logger = logging.getLogger("student_management")

# 导入所有 Model，确保它们在 Base.metadata 中注册后再执行 create_all
from app.models import *  # noqa: F403, F401

# 导入所有 API 路由模块
from app.api import auth, course_selection, classroom, score, repair, schedule, admin
from app.api import leave, advisor, training_plan, graduation, notification, internal, profile, exam

# 导入服务层
from app.services import ws_manager, event_bus, notification_service
from app.services.event_bus import Events


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 开发模式：自动建表（生产环境应使用 `alembic upgrade head`）
    if settings.debug_sql:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Dev mode: tables auto-created via create_all")
    _register_event_handlers()
    yield
    await async_engine.dispose()


def _register_event_handlers():
    async def on_leave_submitted(db=None, leave=None, student_name=None, **kwargs):
        try:
            async with AsyncSessionLocal() as session:
                await notification_service.create_notification(
                    db=session,
                    title="新请假申请",
                    content=f"学生 {student_name} 提交了 {leave.total_days} 天请假申请",
                    recipient_role="teacher",
                    event_type=Events.LEAVE_SUBMITTED,
                )
                await session.commit()
        except Exception:
            logger.error("on_leave_submitted failed", exc_info=True)

    async def on_leave_approved(db=None, leave=None, **kwargs):
        try:
            async with AsyncSessionLocal() as session:
                await notification_service.create_notification(
                    db=session,
                    title="请假已通过",
                    content=f"请假申请（{leave.total_days}天）已通过审批",
                    recipient_id=leave.student_id,
                    event_type=Events.LEAVE_APPROVED,
                )
                await session.commit()
        except Exception:
            logger.error("on_leave_approved failed", exc_info=True)

    async def on_leave_rejected(db=None, leave=None, **kwargs):
        try:
            async with AsyncSessionLocal() as session:
                await notification_service.create_notification(
                    db=session,
                    title="请假已驳回",
                    content=f"请假申请（{leave.total_days}天）已被驳回",
                    recipient_id=leave.student_id,
                    event_type=Events.LEAVE_REJECTED,
                )
                await session.commit()
        except Exception:
            logger.error("on_leave_rejected failed", exc_info=True)

    event_bus.subscribe(Events.LEAVE_SUBMITTED, on_leave_submitted)
    event_bus.subscribe(Events.LEAVE_APPROVED, on_leave_approved)
    event_bus.subscribe(Events.LEAVE_REJECTED, on_leave_rejected)


app = FastAPI(
    title="大学生管理系统",
    description="学生选课、课表管理、成绩管理、请假审批、毕业审核的一体化平台",
    version="0.3.0",
    lifespan=lifespan,
)

# 速率限制 — slowapi 基于 IP 的请求限流
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# CORS 中间件 — 来源从 settings.allowed_origins 配置（逗号分隔），缺省回退到 localhost:5175
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()] if settings.allowed_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求ID追踪 + 全局异常处理
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(Exception, global_exception_handler)

# 注册所有路由模块
app.include_router(auth.router)
app.include_router(course_selection.router)
app.include_router(classroom.router)
app.include_router(score.router)
app.include_router(repair.router)
app.include_router(schedule.router)
app.include_router(admin.router)
app.include_router(leave.router)
app.include_router(advisor.router)
app.include_router(training_plan.router)
app.include_router(graduation.router)
app.include_router(notification.router)
app.include_router(internal.router)
app.include_router(profile.router)
app.include_router(exam.router)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4001)
        return
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload["sub"]
    except JWTError:
        await ws.close(code=4001)
        return

    await ws_manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, ws)
    except Exception:
        await ws_manager.disconnect(user_id, ws)


@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "healthy", "service": "student-management-system"}


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
