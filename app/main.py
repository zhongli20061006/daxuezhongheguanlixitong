"""
FastAPI 应用入口
使用 lifespan 管理应用生命周期（替代已废弃的 @app.on_event）
增加 WebSocket 支持、APScheduler 定时任务、事件总线通知
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from app.database import async_engine, Base, AsyncSessionLocal
from app.config import settings

# 导入所有 Model，确保它们在 Base.metadata 中注册后再执行 create_all
from app.models import *  # noqa: F403, F401

# 导入所有 API 路由模块
from app.api import auth, course_selection, classroom, score, repair, schedule, admin
from app.api import leave, advisor, training_plan, graduation, notification, internal, profile

# 导入服务层
from app.services import ws_manager, event_bus, notification_service
from app.services.event_bus import Events


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"on_leave_submitted failed: {e}")

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
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"on_leave_approved failed: {e}")

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
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"on_leave_rejected failed: {e}")

    event_bus.subscribe(Events.LEAVE_SUBMITTED, on_leave_submitted)
    event_bus.subscribe(Events.LEAVE_APPROVED, on_leave_approved)
    event_bus.subscribe(Events.LEAVE_REJECTED, on_leave_rejected)


app = FastAPI(
    title="大学生管理系统",
    description="学生选课、课表管理、成绩管理、请假审批、毕业审核的一体化平台",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
