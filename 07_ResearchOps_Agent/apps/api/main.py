"""ResearchOps Agent 的 FastAPI 应用入口。

该文件只承担 HTTP 接入层职责：

1. 创建 FastAPI 应用；
2. 声明 API 路由；
3. 调用 TaskPlanningService 或 Readiness Assessment Service；
4. 将校验异常和业务异常转换为统一错误响应。

LangGraph 节点和计划生成逻辑不直接写入路由函数。
"""

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from researchops.core.access_context import authorize_resource
from researchops.core.access_middleware import (
    COOKIE_NAME,
    EXCHANGE_PATH,
    SESSION_PATH,
    AccessMiddleware,
    error_response,
)
from researchops.core.config import get_settings
from researchops.core.logging import configure_logging, get_logger
from researchops.schemas import (
    AssessmentFeedbackRequest,
    AssessmentFeedbackResponse,
    AssessmentJobResponse,
    AssessmentRequest,
    AssessmentRevisionHistory,
    EnvironmentAuthorizationResponse,
    ErrorDetail,
    ErrorResponse,
    FinalInvestmentDecisionRecord,
    FinalInvestmentDecisionRequest,
    HealthResponse,
    ReadinessAssessment,
    TargetResolutionRequest,
    TargetResolutionResponse,
    TaskRequest,
    TaskResponse,
)
from researchops.services import (
    AssessmentFeedbackTargetError,
    AssessmentJobNotFoundError,
    AssessmentJobService,
    AssessmentReviewNotFoundError,
    DurableAssessmentReviewStore,
    EnvironmentAuthorizationService,
    ModelBackedReadinessWorkflowService,
    ReadinessAssessmentService,
    TargetResolutionError,
    TargetResolutionService,
    TaskPlanningError,
    TaskPlanningService,
)
from researchops.services.access_store import AccessError, AccessStore
from researchops.services.execution_control import run_controlled

settings = get_settings()
logger = get_logger("api")


class ReadinessExecutionError(RuntimeError):
    """Readiness 主链发生未预期技术失败。"""


class EnvironmentAuthorizationError(ValueError):
    """只读环境授权令牌无效或已过期。"""


# 应用启动时统一初始化结构化日志。
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(application):
    if settings.deployment_mode == "public":
        store = get_access_store()
        store.acquire_instance()
        try:
            yield
        finally:
            store.release_instance()
    else:
        yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=("面向人工智能论文复现任务的规划与执行 Agent。"),
    lifespan=lifespan,
    docs_url=None if settings.deployment_mode == "public" else "/docs",
    redoc_url=None if settings.deployment_mode == "public" else "/redoc",
    openapi_url=None if settings.deployment_mode == "public" else "/openapi.json",
)


def get_access_store() -> AccessStore:
    if not hasattr(app.state, "access_store"):
        app.state.access_store = AccessStore(settings)
    store = app.state.access_store
    now = store.clock()
    if now - getattr(store, "last_cleanup", 0) >= 60:
        store.cleanup()
        store.last_cleanup = now
    return store


app.add_middleware(AccessMiddleware, settings=settings, store_provider=get_access_store)


@app.exception_handler(AccessError)
async def handle_access_error(_request: Request, exc: AccessError):
    return error_response(exc)


class InvitationExchange(BaseModel):
    invitation_code: str = Field(max_length=200)


@app.post(EXCHANGE_PATH, include_in_schema=False)
def exchange_invitation(payload: InvitationExchange):
    token, session = get_access_store().exchange(payload.invitation_code)
    response = JSONResponse(session)
    response.set_cookie(
        COOKIE_NAME,
        token,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=max(1, int(session["expires_at"] - get_access_store().clock())),
    )
    return response


@app.get(SESSION_PATH, include_in_schema=False)
def access_session(request: Request):
    if settings.deployment_mode == "local":
        return {"local_mode": True, "csrf_token": "", "environment_readonly": True}
    return {**request.state.access_session, "environment_readonly": False}


@app.delete(SESSION_PATH, include_in_schema=False)
def logout_access(request: Request):
    get_access_store().logout(request.cookies.get(COOKIE_NAME))
    response = JSONResponse({"logged_out": True})
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="strict")
    return response


@app.get("/api/v1/readiness", include_in_schema=False)
def application_readiness():
    get_access_store().cleanup()
    return {
        "ready": True,
        "model_configured": bool(
            settings.llm_api_key and settings.llm_api_key.get_secret_value().strip()
        ),
    }


# 工作流在应用启动时编译一次，后续请求复用同一个图结构。
task_planning_service = TaskPlanningService()
target_resolution_service = TargetResolutionService()
readiness_assessment_service = ReadinessAssessmentService(
    target_resolution_service=target_resolution_service
)
readiness_workflow_service = ModelBackedReadinessWorkflowService(
    readiness_assessment_service,
    review_store=DurableAssessmentReviewStore(settings),
)
environment_authorization_service = EnvironmentAuthorizationService()
assessment_job_service = AssessmentJobService(readiness_workflow_service)

MVP_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "mvp"


@app.exception_handler(AssessmentJobNotFoundError)
async def handle_assessment_job_not_found(
    _request: Request,
    exc: AssessmentJobNotFoundError,
) -> JSONResponse:
    response = ErrorResponse(
        error_code="ASSESSMENT_JOB_NOT_FOUND",
        message=str(exc),
        details=[],
        task_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(AssessmentReviewNotFoundError)
async def handle_assessment_review_not_found(
    _request: Request,
    exc: AssessmentReviewNotFoundError,
) -> JSONResponse:
    response = ErrorResponse(
        error_code="ASSESSMENT_REVIEW_NOT_FOUND",
        message=str(exc),
        details=[],
        task_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(AssessmentFeedbackTargetError)
async def handle_assessment_feedback_target_error(
    _request: Request,
    exc: AssessmentFeedbackTargetError,
) -> JSONResponse:
    response = ErrorResponse(
        error_code="ASSESSMENT_FEEDBACK_TARGET_INVALID",
        message=str(exc),
        details=[],
        task_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """将 FastAPI/Pydantic 校验异常转换为统一错误结构。"""

    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
            error_type=error["type"],
        )
        for error in exc.errors()
    ]

    response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="请求参数校验失败。",
        details=details,
        task_id=None,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(TaskPlanningError)
async def handle_task_planning_error(
    _request: Request,
    exc: TaskPlanningError,
) -> JSONResponse:
    """将任务规划业务异常转换为统一错误响应。"""

    details = [ErrorDetail(message=detail) for detail in exc.details]

    response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        details=details,
        task_id=exc.task_id,
    )

    http_status = (
        status.HTTP_500_INTERNAL_SERVER_ERROR
        if exc.error_code == "INTERNAL_ERROR"
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )

    return JSONResponse(
        status_code=http_status,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(TargetResolutionError)
async def handle_target_resolution_error(
    _request: Request,
    exc: TargetResolutionError,
) -> JSONResponse:
    """将未完成目标解析的 Assessment 请求转换为可读错误。"""

    response = ErrorResponse(
        error_code="TARGET_NOT_RESOLVED",
        message=str(exc),
        details=[],
        task_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(ReadinessExecutionError)
async def handle_readiness_execution_error(
    _request: Request,
    _exc: ReadinessExecutionError,
) -> JSONResponse:
    """隐藏内部实现细节并返回统一 Readiness 技术错误。"""

    response = ErrorResponse(
        error_code="READINESS_EXECUTION_FAILED",
        message="Readiness Assessment 暂时无法完成，请重试。",
        details=[],
        task_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(EnvironmentAuthorizationError)
async def handle_environment_authorization_error(
    _request: Request,
    _exc: EnvironmentAuthorizationError,
) -> JSONResponse:
    """无效授权不读取环境，并返回可重新授权的安全错误。"""

    response = ErrorResponse(
        error_code="ENVIRONMENT_AUTHORIZATION_INVALID",
        message="只读环境授权无效或已过期，请重新确认授权。",
        details=[],
        task_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(mode="json"),
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="检查服务健康状态",
)
def health_check() -> HealthResponse:
    """返回服务名称、运行状态和版本号。"""

    return HealthResponse(
        service=settings.app_name,
        status="ok",
        version=settings.app_version,
    )


@app.post(
    "/api/v1/tasks/plan",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "请求校验或计划生成失败。",
        },
        500: {
            "model": ErrorResponse,
            "description": "服务内部执行失败。",
        },
    },
    tags=["tasks"],
    summary="生成论文复现计划",
)
def create_reproduction_plan(
    request: TaskRequest,
) -> TaskResponse:
    """创建 task_id、运行 LangGraph 并返回结构化复现计划。"""

    return task_planning_service.create_plan(request)


@app.post(
    "/api/v1/targets/resolve",
    response_model=TargetResolutionResponse,
    tags=["targets"],
    summary="解析或规范化 Assessment 目标",
)
def resolve_assessment_target(
    request: TargetResolutionRequest,
) -> TargetResolutionResponse:
    """统一处理 Repository、Project page、DOI、arXiv 与论文标题。"""

    return target_resolution_service.resolve(request)


@app.post(
    "/api/v1/environment-authorizations",
    response_model=EnvironmentAuthorizationResponse,
    tags=["environment"],
    summary="确认本次只读环境检测授权",
)
def authorize_readonly_environment() -> EnvironmentAuthorizationResponse:
    """由明确授权按钮触发，并仅在当前进程内保存短期令牌。"""

    if settings.deployment_mode == "public":
        raise AccessError("ENVIRONMENT_DISABLED", "公网不支持服务器环境探测。", 403)
    grant = environment_authorization_service.issue()
    return EnvironmentAuthorizationResponse(
        authorization_token=grant.token,
        expires_at=grant.expires_at,
    )


@app.post(
    "/api/v1/assessments",
    response_model=ReadinessAssessment,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "目标尚未解析、候选尚未确认或请求字段无效。",
        },
        500: {
            "model": ErrorResponse,
            "description": "Readiness Assessment 技术执行失败。",
        },
    },
    tags=["assessments"],
    summary="创建 Readiness Assessment",
)
def create_readiness_assessment(
    request: AssessmentRequest,
) -> ReadinessAssessment:
    """运行真实 AI → Rule 主链并返回可追溯的保守评估结果。"""

    if settings.deployment_mode == "public" and (
        request.environment_authorized or request.environment_mode == "readonly"
    ):
        raise AccessError("ENVIRONMENT_DISABLED", "公网不支持服务器环境探测。", 403)
    if request.environment_authorized and not environment_authorization_service.validate(
        request.environment_authorization_token
    ):
        raise EnvironmentAuthorizationError

    try:
        return run_controlled(lambda: readiness_workflow_service.create_assessment(request))
    except (TargetResolutionError, AccessError):
        raise
    except Exception as exc:
        logger.exception("Readiness Assessment execution failed")
        raise ReadinessExecutionError from exc


@app.post(
    "/api/v1/assessment-jobs",
    response_model=AssessmentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["assessments"],
    summary="启动可查询真实阶段的 Readiness Assessment",
)
def start_readiness_assessment_job(
    request: AssessmentRequest,
) -> AssessmentJobResponse:
    """后台运行 AI → Rule 主链；进度只反映已到达的工作流阶段。"""

    if settings.deployment_mode == "public" and (
        request.environment_authorized or request.environment_mode == "readonly"
    ):
        raise AccessError("ENVIRONMENT_DISABLED", "公网不支持服务器环境探测。", 403)
    if request.environment_authorized and not environment_authorization_service.validate(
        request.environment_authorization_token
    ):
        raise EnvironmentAuthorizationError
    return assessment_job_service.start(request)


@app.get(
    "/api/v1/assessment-jobs/{job_id}",
    response_model=AssessmentJobResponse,
    tags=["assessments"],
    summary="查询 Readiness Assessment 的真实处理阶段",
)
def get_readiness_assessment_job(job_id: UUID) -> AssessmentJobResponse:
    """返回阶段、范围计数和最终 Assessment，不伪造百分比进度。"""

    return assessment_job_service.get(job_id)


@app.get(
    "/api/v1/assessments/{assessment_id}",
    response_model=ReadinessAssessment,
    tags=["assessments"],
    summary="读取最新 Assessment 裁决及脱敏审计链",
)
def get_readiness_assessment(assessment_id: UUID) -> ReadinessAssessment:
    """只返回领域结果和审计元数据，不返回 MaterialBundle 或原始 Prompt。"""

    return readiness_workflow_service.get_assessment(assessment_id)


@app.get(
    "/api/v1/assessments/{assessment_id}/revisions",
    response_model=AssessmentRevisionHistory,
    tags=["assessments"],
    summary="读取 Assessment revision 历史及相邻版本差异",
)
def get_readiness_assessment_revisions(
    assessment_id: UUID,
) -> AssessmentRevisionHistory:
    """仅返回 Assessment 快照与安全 diff，不返回原始材料或 Prompt。"""

    return readiness_workflow_service.get_assessment_revision_history(assessment_id)


@app.post(
    "/api/v1/assessments/{assessment_id}/feedback",
    response_model=AssessmentFeedbackResponse,
    status_code=status.HTTP_200_OK,
    tags=["assessments"],
    summary="提交 Evidence / Finding 反馈并按需重新裁决",
)
def submit_assessment_feedback(
    assessment_id: UUID,
    request: AssessmentFeedbackRequest,
) -> AssessmentFeedbackResponse:
    """记录 Human 反馈；只有可验证的修正才进入 AI → Rule 重评。"""

    authorize_resource("assessment", assessment_id)
    try:
        return run_controlled(
            lambda: readiness_workflow_service.submit_feedback(assessment_id, request)
        )
    except (AssessmentReviewNotFoundError, AssessmentFeedbackTargetError, AccessError):
        raise
    except Exception as exc:
        logger.exception("Readiness feedback execution failed")
        raise ReadinessExecutionError from exc


@app.post(
    "/api/v1/assessments/{assessment_id}/final-decision",
    response_model=FinalInvestmentDecisionRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["assessments"],
    summary="记录用户最终投入决定",
)
def record_final_investment_decision(
    assessment_id: UUID,
    request: FinalInvestmentDecisionRequest,
) -> FinalInvestmentDecisionRecord:
    """保存 Human 决定，但不修改 Rule Gate 或授予执行权限。"""

    return readiness_workflow_service.record_final_decision(assessment_id, request)


# 开发版 HTML 与 API 同源提供，避免本地演示依赖额外前端服务器。
app.mount(
    "/mvp",
    StaticFiles(directory=MVP_FRONTEND_DIR, html=True),
    name="mvp",
)
