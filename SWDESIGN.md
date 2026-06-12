# Agentic DevOps Starter 소프트웨어 설계 문서

현재 코드베이스 기준의 상세 설계 문서이다. FastAPI 백엔드, GitHub Copilot SDK 세션, AG-UI 스타일 SSE 스트리밍, React/Vite 프론트엔드, Azure App Service 배포 인프라를 코드 레벨 구성요소와 런타임 흐름 중심으로 설명한다.

| 항목 | 내용 |
| --- | --- |
| 문서 파일 | `SWDESIGN.md` |
| HTML 버전 | `SWDESIGN.html` |
| 대상 저장소 | `agentic-devops-starter` |
| 주요 런타임 | Python 3.12, FastAPI, React 18, Vite |
| 배포 대상 | Azure App Service + ACR + Blob Storage |

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [백엔드 상세 설계](#3-백엔드-상세-설계)
4. [백엔드 코드 레벨 매핑](#4-백엔드-코드-레벨-매핑)
5. [일반 채팅 스트리밍 흐름](#5-일반-채팅-스트리밍-흐름)
6. [Copilot 세션 풀 설계](#6-copilot-세션-풀-설계)
7. [파일 업로드/Blob 설계](#7-파일-업로드blob-설계)
8. [Fleet / Infinite Session 작업 설계](#8-fleet--infinite-session-작업-설계)
9. [Agent Teams 설계](#9-agent-teams-설계)
10. [Agent Skills 설계](#10-agent-skills-설계)
11. [프론트엔드 상세 설계](#11-프론트엔드-상세-설계)
12. [프론트엔드 코드 레벨 매핑](#12-프론트엔드-코드-레벨-매핑)
13. [데이터 모델 및 이벤트 스키마](#13-데이터-모델-및-이벤트-스키마)
14. [배포/인프라 설계](#14-배포인프라-설계)
15. [보안 설계](#15-보안-설계)
16. [로깅/관측성](#16-로깅관측성)
17. [제한 사항과 개선 후보](#17-제한-사항과-개선-후보)

## 1. 시스템 개요

Agentic DevOps Starter는 브라우저 기반 채팅 UI에서 입력한 메시지를 FastAPI 백엔드로 전달하고, 백엔드가 GitHub Copilot SDK 세션을 통해 응답을 생성한 뒤 SSE로 프론트엔드에 스트리밍하는 풀스택 애플리케이션이다. 단일 채팅뿐 아니라 파일 첨부, 병렬 프롬프트 실행, 반복 추론, 역할 기반 다중 에이전트 팀 실행을 지원한다.

| 영역 | 현재 구현 | 주요 코드 |
| --- | --- | --- |
| AI 런타임 | GitHub Copilot SDK의 `CopilotClient`, `CopilotSession` 사용 | `app/agui_server.py`, `app/src/state.py` |
| API | FastAPI + StreamingResponse 기반 SSE | `app/src/routes.py` |
| 프론트엔드 | React 18, TypeScript, Vite, Zustand | `app/frontend/src/*` |
| 파일 저장 | Azure Blob Storage, `DefaultAzureCredential` | `blob_storage.py`, `file_validation.py` |
| 배포 | nginx + FastAPI 단일 컨테이너를 Azure App Service에 배포 | `app/Dockerfile.appservice`, `infra/*` |

## 2. 전체 아키텍처

```
+-------------------+
| Browser / React   |
| - ChatInterface   |
| - TeamsSidebar    |
| - Zustand Stores  |
+---------+---------+
          |
          | /api/*  (dev: Vite proxy, prod: nginx)
          v
+-------------------+        +------------------------+
| Proxy Layer       |        | Static Frontend        |
| - Vite dev server |        | - nginx serves dist    |
| - nginx :8080     |        | - SPA fallback         |
+---------+---------+        +------------------------+
          |
          | prefix stripped: /api/v1/... -> /v1/...
          v
+-----------------------------+
| FastAPI Backend :5100       |
| - routes.py                 |
| - SessionPool               |
| - Job Manager               |
| - Team Orchestrator         |
| - BlobStorageService        |
+------+----------+----------+
       |          |
       |          +--------------------+
       v                               v
+----------------------+       +----------------------+
| GitHub Copilot SDK   |       | Azure Blob Storage   |
| CopilotClient        |       | uploads container    |
| CopilotSession       |       | private endpoint     |
+----------------------+       +----------------------+
```

### 2.1 핵심 설계 원칙

- 프록시 경계 명확화: 백엔드에는 `/api` prefix를 두지 않고, Vite/nginx 계층에서만 사용한다.
- 세션 단위 대화 유지: `thread_id`별 Copilot SDK 세션을 유지해 멀티턴 대화 맥락을 보존한다.
- SSE 우선: 채팅과 Agent Teams 모두 fetch 기반 HTTP streaming으로 구현한다.
- 역할 분리: API 라우팅, 세션 관리, 작업 관리, 팀 오케스트레이션, Blob 접근을 별도 모듈로 분리한다.
- 운영 단순성: App Service 단일 컨테이너 안에서 nginx와 FastAPI를 supervisor로 함께 실행한다.

## 3. 백엔드 상세 설계

### 3.1 FastAPI 앱 생명주기

`app/agui_server.py`의 `create_app()` 함수가 FastAPI 앱을 생성한다. 앱 lifespan에서 Copilot SDK 클라이언트를 시작하고, 세션 풀과 유휴 세션 정리 task를 설정한다.

```
def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        github_token = os.environ.get("GITHUB_TOKEN")
        client = CopilotClient(github_token=github_token) if github_token else CopilotClient()
        await client.start()
        set_client(client)

        pool = SessionPool(idle_timeout=settings.session_timeout)
        set_session_pool(pool)
        cleanup_task = asyncio.create_task(_idle_cleanup_loop(pool))

        yield

        cleanup_task.cancel()
        await pool.shutdown()
        await client.stop()
```

| 단계 | 코드 레벨 동작 | 설계 의도 |
| --- | --- | --- |
| 환경 로드 | `load_dotenv()`, `Settings` | 로컬 개발과 운영 환경 변수 사용 방식 통일 |
| Copilot client 시작 | `CopilotClient(config)`, `await client.start()` | 요청마다 client를 만들지 않고 앱 단위 singleton으로 재사용 |
| SessionPool 설정 | `set_session_pool(pool)` | 라우트에서 전역 accessor로 thread별 세션 접근 |
| idle cleanup | 30초마다 `pool.cleanup_idle()` | 장시간 미사용 Copilot 세션 정리 |
| 종료 처리 | `pool.shutdown()`, `client.stop()` | 프로세스 종료 시 SDK subprocess와 세션 연결 정리 |

### 3.2 미들웨어와 보안 헤더

FastAPI 미들웨어는 모든 응답에 기본 보안 헤더를 추가한다. 운영 컨테이너의 nginx도 동일한 계열의 헤더를 추가하므로 프록시 및 직접 접근 모두에서 방어적 기본값을 갖는다.

```
@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

### 3.3 CORS

`CORS_ORIGINS` 환경 변수가 비어 있으면 기본값은 `http://localhost:5173`, `http://127.0.0.1:5173`이다. 현재 Vite dev server는 `8080`을 사용하므로 실제 개발은 프록시 경유가 기본 흐름이다.

## 4. 백엔드 코드 레벨 매핑

### 4.1 모듈별 책임

| 파일 | 핵심 함수/클래스 | 책임 |
| --- | --- | --- |
| `app/agui_server.py` | `create_app()`, `_idle_cleanup_loop()` | FastAPI 앱 생성, CopilotClient lifecycle, 미들웨어, CORS, router 등록 |
| `app/src/routes.py` | `agent_endpoint()`, `upload_file()`, `teams_stream()` | HTTP 라우트와 SSE 응답 구성 |
| `app/src/state.py` | `SessionPool`, `get_client()`, `get_session_pool()` | CopilotClient singleton 및 thread별 CopilotSession 관리 |
| `app/src/jobs.py` | `create_job()`, `run_fleet()`, `run_infinite_session()` | 메모리 기반 비동기 작업 관리 |
| `app/src/orchestrator.py` | `run_teams()`, `_stream_agent()`, flow runner들 | 다중 역할 Copilot session 오케스트레이션 |
| `app/src/patterns.py` | `Pattern`, `AgentRole`, `PATTERNS` | Agent Team 패턴과 역할별 system prompt 정의 |
| `app/src/skills.py` | `load_skills()`, `get_skill_directories()`, `get_disabled_skills()` | SKILL.md 디렉터리 디스커버리 및 SDK 전달용 경로 해석 |
| `app/src/blob_storage.py` | `BlobStorageService`, `get_blob_service()` | Azure Blob upload/download |
| `app/src/file_validation.py` | `validate_file_type()`, `validate_file_size()`, `generate_blob_name()` | 파일 확장자/MIME/크기/파일명 sanitization |

### 4.2 API 라우트와 함수 매핑

| HTTP | 라우트 | 함수 | 반환 타입/형태 | 주요 의존성 |
| --- | --- | --- | --- | --- |
| GET | `/health` | `health_check()` | `{"status": "healthy"}` | 없음 |
| POST | `/` | `agent_endpoint()` | `StreamingResponse(text/event-stream)` | `SessionPool`, `CopilotSession`, `_resolve_attachments()` |
| POST | `/v1/files/upload` | `upload_file()` | `UploadResult` 또는 error JSON | `file_validation`, `BlobStorageService` |
| DELETE | `/v1/threads/{thread_id}` | `delete_thread()` | `{"status": "deleted"}` | `SessionPool.disconnect()` |
| POST | `/v1/fleet` | `fleet_endpoint()` | 202 + `{"job_id": ...}` | `create_job()`, `run_fleet()` |
| POST | `/v1/infinite-session` | `infinite_session_endpoint()` | 202 + `{"job_id": ...}` | `create_job()`, `run_infinite_session()` |
| GET | `/v1/patterns` | `list_patterns()` | `list[PatternInfo]` | `PATTERNS` |
| POST | `/v1/teams/stream` | `teams_stream()` | `StreamingResponse(text/event-stream)` | `run_teams()`, `_resolve_attachments()` |
| GET | `/v1/jobs/{job_id}` | `job_status_endpoint()` | `JobStatusResponse` | `get_job()` |

## 5. 일반 채팅 스트리밍 흐름

### 5.1 서버 내부 알고리즘

`agent_endpoint()`는 요청 body에서 thread/run/message/attachment 정보를 추출한 뒤, 내부 async generator를 만들어 `StreamingResponse`로 반환한다.

```
input_data = await request.json()
thread_id = input_data.get("thread_id") or uuid.uuid4().hex[:12]
run_id = input_data.get("run_id") or uuid.uuid4().hex[:12]
messages = input_data.get("messages", [])
attachments = input_data.get("attachments")

prompt = _build_prompt(messages, attachments)
```

#### 프롬프트 생성 규칙

1. `messages` 중 마지막 `role == "user"` 메시지를 선택한다.
1. 사용자 메시지가 없으면 마지막 메시지를 fallback으로 사용한다.
1. 첨부 파일이 있으면 `_resolve_attachments()`로 파일 컨텍스트를 앞에 붙인다.

```
def _build_prompt(messages, attachments=None) -> str:
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        content = user_messages[-1].get("content", "")
    elif messages:
        content = messages[-1].get("content", "")
    else:
        content = ""

    if attachments:
        file_context = _resolve_attachments(attachments)
        if file_context:
            content = file_context + "\n\n" + content

    return content
```

### 5.2 Copilot SDK 이벤트 변환

Copilot SDK callback은 동기 함수 형태로 호출되므로, FastAPI async generator와 안전하게 연결하기 위해 `loop.call_soon_threadsafe()`와 `asyncio.Queue`를 사용한다.

| Copilot SDK 이벤트 | 서버 내부 큐 메시지 | SSE 이벤트 |
| --- | --- | --- |
| `AssistantMessageDeltaData` | `{"type": "delta", "content": delta.delta_content}` | `TEXT_MESSAGE_CONTENT` |
| `SessionErrorData` | `{"type": "error", "content": err.message}` | `RUN_ERROR` |
| `SessionIdleData` | `idle_event.set()` | 스트림 종료 준비 |

```
Frontend                  FastAPI                         CopilotSession
   | POST /api/              |                                  |
   |------------------------>|                                  |
   |                         | get_or_create(thread_id)         |
   |                         |--------------------------------->|
   |                         | session.send(prompt)             |
   |                         |--------------------------------->|
   | <-- RUN_STARTED --------|                                  |
   | <-- TEXT_MESSAGE_START -| <-- AssistantMessageDeltaData ---|
   | <-- CONTENT delta* -----|                                  |
   |                         | <-- SessionIdleData -------------|
   | <-- TEXT_MESSAGE_END ---|                                  |
   | <-- RUN_FINISHED -------|                                  |
```

### 5.3 SSE wire format

서버의 `_sse()` 헬퍼는 JSON 객체를 SSE data line으로 감싼다.

```
def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"
```

예시:

```
data: {"type": "RUN_STARTED", "thread_id": "abc123", "run_id": "def456"}

data: {"type": "TEXT_MESSAGE_START", "message_id": "m001"}

data: {"type": "TEXT_MESSAGE_CONTENT", "delta": "안녕하세요"}

data: {"type": "TEXT_MESSAGE_END", "message_id": "m001"}

data: {"type": "RUN_FINISHED", "thread_id": "abc123", "run_id": "def456"}
```

## 6. Copilot 세션 풀 설계

`SessionPool`은 `thread_id`별 Copilot SDK 세션을 유지한다. 동일 thread에 대한 동시 접근을 막기 위해 thread별 `asyncio.Lock`을 사용하고, pool dictionary 자체는 `_pool_lock`으로 보호한다.

```
class SessionPool:
    def __init__(self, idle_timeout: float = 120.0) -> None:
        self._sessions: dict[str, CopilotSession] = {}
        self._last_active: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()
        self._idle_timeout = idle_timeout
```

### 6.1 get_or_create(thread_id)

| 단계 | 코드 동작 | 의미 |
| --- | --- | --- |
| 락 준비 | `if thread_id not in self._locks: self._locks[thread_id] = asyncio.Lock()` | thread별 직렬화 보장 |
| 기존 세션 반환 | `session = self._sessions.get(thread_id)` | 이미 활성화된 세션이면 재사용 |
| resume 시도 | `client.resume_session(thread_id, ...)` | SDK가 저장한 세션을 이어받음 |
| create fallback | `client.create_session(session_id=thread_id, ...)` | resume 실패 시 신규 세션 생성 |
| 활성 시간 기록 | `self._last_active[thread_id] = time.monotonic()` | idle cleanup 판단 기준 |

운영상 주의: 세션 풀은 프로세스 메모리에 있다. App Service scale-out으로 인스턴스가 여러 개가 되면 thread별 세션이 인스턴스 간 공유되지 않는다. Sticky session 또는 외부 session coordination이 필요한 요구사항이 생길 수 있다.

## 7. 파일 업로드/Blob 설계

### 7.1 업로드 처리 순서

```
Browser
  -> fileUploadService.uploadFile()
  -> XMLHttpRequest POST /api/v1/files/upload
  -> FastAPI upload_file(file: UploadFile)
  -> validate_file_type(content_type, filename)
  -> resolve_content_type(content_type, filename)
  -> await file.read()
  -> validate_file_size(len(content))
  -> generate_blob_name(filename)
  -> BlobStorageService.upload(content, blob_name, content_type)
  -> UploadResult JSON
```

### 7.2 서버 검증 코드

```
MAX_FILE_SIZE_BYTES = 10_485_760
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".txt", ".csv", ".json", ".md",
}

def validate_file_size(size: int) -> None:
    if size <= 0:
        raise ValueError("File is empty")
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError("File exceeds maximum size of 10MB")
```

### 7.3 파일명 sanitization

`generate_blob_name()`은 경로 traversal을 방지하기 위해 `\`와 `/`를 모두 고려해 basename만 추출하고, 선행 dot을 제거한 뒤 안전하지 않은 문자를 underscore로 바꾼다.

```
def generate_blob_name(filename: str) -> str:
    basename = filename.replace("\\", "/").split("/")[-1].lstrip(".")
    if not basename:
        basename = "unnamed"
    basename = re.sub(r"[^\w.\-]", "_", basename)
    return f"{uuid.uuid4().hex}_{basename}"
```

### 7.4 오류 응답 설계

| 조건 | HTTP | error | 프론트엔드 처리 |
| --- | --- | --- | --- |
| 허용되지 않은 확장자/MIME | 415 | `INVALID_TYPE` | `UploadError.detail` 표시 |
| 빈 파일 | 422 | `EMPTY_FILE` | 업로드 실패 상태 |
| 10MB 초과 | 413 | `FILE_TOO_LARGE` | 최대 크기 안내 |
| Blob endpoint 미설정 | 503 | `STORAGE_NOT_CONFIGURED` | 서버 설정 오류로 표시 |
| Blob 업로드 실패 | 502 | `UPLOAD_FAILED` | 재시도 가능 오류 |

### 7.5 첨부 파일 프롬프트 주입

채팅과 Agent Teams 모두 attachment metadata를 받으면 서버에서 Blob을 다운로드해 prompt 앞부분에 파일 컨텍스트를 삽입한다. 텍스트/JSON은 문자열로, 그 외는 base64로 포함한다.

## 8. Fleet / Infinite Session 작업 설계

`jobs.py`는 외부 큐 없이 프로세스 메모리에 작업 상태를 저장하는 단순 job manager이다. API는 작업을 즉시 실행하지 않고 job id를 반환하며, 실제 실행은 `asyncio.create_task()`로 백그라운드에서 진행된다.

```
_jobs: dict[str, JobStatusResponse] = {}

def create_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = JobStatusResponse(
        job_id=job_id,
        status="pending",
        created_at=datetime.now(UTC).isoformat(),
    )
    return job_id
```

### 8.1 Fleet

- `FleetRequest.items`는 Pydantic에서 최소 1개, 최대 20개로 제한된다.
- 각 item은 별도 Copilot session으로 실행된다.
- 내부 semaphore도 20으로 설정되어 API 제한과 실행 제한이 일치한다.
- 개별 item 실패는 전체 실패가 아니라 `ERROR: ...` 문자열로 결과 배열에 들어간다.

```
async def run_fleet(job_id: str, items: list[tuple[str, str | None]]) -> None:
    job = _jobs[job_id]
    job.status = "running"
    semaphore = asyncio.Semaphore(20)

    async def _process(prompt: str, system_message: str | None) -> str:
        async with semaphore:
            return await _call_session(prompt, system_message)
```

### 8.2 Infinite Session

Infinite Session은 output chaining 방식이다. 첫 prompt 결과가 다음 prompt가 되며, 마지막 결과만 `job.result`에 저장된다. `iterations`는 모델에서 1~10으로 제한된다.

```
current_prompt = prompt
for _ in range(iterations):
    current_prompt = await _call_session(current_prompt, system_message)

job.result = current_prompt
job.status = "completed"
```

## 9. Agent Teams 설계

### 9.1 패턴 정의

`patterns.py`는 `Pattern`과 `AgentRole` 모델을 정의하고, 서버 로드 시 `src/data/patterns.yaml`에서
패턴 ID별 역할 목록과 flow type을 불러온다.

```
class AgentRole(BaseModel):
    name: str
    emoji: str
    system_prompt: str

class Pattern(BaseModel):
    id: str
    name: str
    description: str
    roles: list[AgentRole]
    flow_type: str
    max_rounds: int = 3
```

| 패턴 ID | flow_type | 실행 함수 | 역할 구조 |
| --- | --- | --- | --- |
| `debate-critic` | `sequential_rounds` | `_run_sequential_rounds()` | Proposer, Opponent, Critic, Synthesizer, Scribe |
| `generator-evaluator` | `feedback_loop` | `_run_feedback_loop()` | Generator, Evaluator, Refiner, Scribe |
| `leadership` | `fan_out_sequential` | `_run_fan_out_sequential()` | CEO, CTO, CISO, CFO, CPO, ChiefOfStaff |
| `planner-executor` | `sequential_tasks` | `_run_sequential_tasks()` | Planner, Executor, Validator, Scribe |
| `research-report` | `research_loop` | `_run_research_loop()` | Researcher, Reasoner, Reporter |

### 9.2 에이전트 실행 단위

`_stream_agent()`는 하나의 역할을 하나의 Copilot session으로 실행하고, session delta를 Agent Teams SSE 이벤트로 변환한다.

```
async def _stream_agent(role: AgentRole, prompt: str, context: str, round_num: int | None = None):
    client = get_client()
    sys_content = role.system_prompt + "\n\nContext:\n" + context
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        system_message={"mode": "replace", "content": sys_content},
        streaming=True,
        available_tools=[],
        skill_directories=get_skill_directories(),
        disabled_skills=get_disabled_skills(),
    )
    await session.send(prompt)
    yield {"type": "AGENT_STARTED", "agent_role": f"{role.emoji} {role.name}"}
```

### 9.3 팀 히스토리

`_teams_history`는 `thread_id`별 이전 실행 결과를 최대 10개 보관한다. 다음 실행 시 `Previous team discussions` 컨텍스트로 삽입된다.

```
_teams_history: dict[str, list[str]] = {}
_MAX_HISTORY_TURNS = 10

def _append_history(thread_id: str | None, run_summary: str) -> None:
    if not thread_id:
        return
    _teams_history.setdefault(thread_id, []).append(run_summary)
    if len(_teams_history[thread_id]) > _MAX_HISTORY_TURNS:
        _teams_history[thread_id] = _teams_history[thread_id][-_MAX_HISTORY_TURNS:]
```

제한: 팀 히스토리는 in-memory이므로 서버 재시작 또는 scale-out 시 공유되지 않는다. 장기 대화/운영 안정성이 필요하면 Redis, Cosmos DB, Azure Table Storage 같은 외부 저장소가 필요하다.

## 10. Agent Skills 설계

Agent Skills는 open [SKILL.md](https://github.com/anthropics/skills) 포맷으로 작성된 디스크 상의 스킬을 Copilot SDK에 전달해, **에이전트(모델)가 사용자 turn에 따라 스스로 필요한 스킬을 선택해 적용**하도록 하는 기능이다. 애플리케이션은 스킬을 직접 실행하거나 프롬프트에 통째로 주입하지 않는다. 단지 `SKILL.md`가 들어 있는 디렉터리 경로만 SDK에 넘기고, **로딩·라우팅·적용은 전적으로 SDK가 담당**한다.

### 10.1 동작 원리 (Progressive Disclosure)

각 스킬은 `<skill-name>/SKILL.md` 형태의 폴더이며, YAML frontmatter(`name`, `description`)와 Markdown 본문(지시문)으로 구성된다. SDK는 점진적 공개(progressive disclosure) 모델로 스킬을 다룬다.

| 단계 | 동작 | 설계 의도 |
| --- | --- | --- |
| 메타데이터 노출 | 모든 스킬의 `description`만 모델 컨텍스트에 노출 | 본문 전체를 항상 로드하지 않아 토큰 비용 최소화 |
| 자체 라우팅 | 모델이 사용자 turn과 `description`을 보고 관련 스킬을 스스로 선택 | 앱 코드가 분기하지 않고 에이전트가 판단 |
| 본문 on-demand 로드 | 선택된 스킬의 본문(instruction body)만 그때 로드 | 관련 없는 turn에서는 컨텍스트를 차지하지 않음 |

즉, **전체 Context를 항상 로드하는 구조가 아니다.** 상시 컨텍스트에 올라가는 것은 가벼운 `description` 메타데이터뿐이고, 무거운 본문은 모델이 관련성을 판단했을 때만 들어간다. 따라서 스킬을 추가해도 토큰 비용이 선형으로 폭증하지 않는다.

### 10.2 스킬 디스커버리

`src.skills.load_skills()`는 앱 시작 시 한 번 실행되어 스킬 디렉터리를 탐색·캐싱한다. 애플리케이션은 **스킬 레지스트리가 아니다** — 스킬을 API로 나열하거나 서빙하지 않으며, SDK가 스캔할 파일시스템 경로만 결정한다.

```
def load_skills() -> list[str]:
    candidates = [_REPO_SKILLS_DIR, *_extra_directories_from_env()]
    resolved = []
    for directory in candidates:
        if not _has_any_skill(directory):   # <name>/SKILL.md 존재 여부 확인
            continue
        resolved.append(str(directory))
    return resolved
```

| 소스 | 결정 방식 | 비고 |
| --- | --- | --- |
| 내장 스킬 | `app/skills/` 디렉터리 | 저장소에 함께 배포되는 기본 스킬 |
| 추가 디렉터리 | `COPILOT_API_SKILL_DIRECTORIES` (`os.pathsep` 또는 `,` 구분) | 운영 환경에서 외부 스킬 경로 주입 |
| 비활성화 | `COPILOT_API_DISABLED_SKILLS` (`,` 구분) | 파일 삭제 없이 특정 스킬만 끄기 |

존재하지 않거나 `SKILL.md`가 없는 디렉터리는 오류가 아니라 조용히 건너뛴다.

### 10.3 SDK 세션 연결

`orchestrator.py`의 모든 Copilot session 생성 지점은 `create_session()` 호출 시 `skill_directories`와 `disabled_skills` 인자를 전달한다. 이 계약 덕분에 일반 채팅과 Agent Teams 양쪽 세션 모두 동일하게 스킬을 활용할 수 있다.

```
session = await client.create_session(
    on_permission_request=PermissionHandler.approve_all,
    system_message={"mode": "replace", "content": sys_content},
    streaming=True,
    available_tools=[],
    skill_directories=get_skill_directories(),
    disabled_skills=get_disabled_skills(),
)
```

전제: 위의 "자체 판단" 동작은 `github-copilot-sdk`의 `create_session(skill_directories=...)`가 progressive-disclosure 라우팅을 구현한다는 데 의존한다. 앱 코드는 경로 전달만 책임지고 라우팅은 SDK에 위임하므로, SDK가 SKILL.md 포맷을 지원하는 한 의도대로 동작한다.

## 11. 프론트엔드 상세 설계

### 11.1 최상위 레이아웃

`App.tsx`는 좌측 팀 패턴 사이드바와 우측 채팅 인터페이스를 배치한다. 테마는 `useTheme()`로 초기화되며, 앱 시작 시 logger에 endpoint와 theme가 기록된다.

```
function App() {
  const { currentTheme } = useTheme();

  useEffect(() => {
    logger.info('Application started', {
      environment: import.meta.env.MODE,
      endpoint: getApiBaseUrl(),
      theme: currentTheme,
    });
  }, [currentTheme]);

  return (
    <div className="min-h-screen bg-primary flex">
      <TeamsSidebar />
      <div className="flex-1 flex flex-col h-screen">
        <ChatInterface />
      </div>
    </div>
  );
}
```

### 11.2 API endpoint 결정

```
export function getApiBaseUrl(): string {
  return import.meta.env.VITE_AGUI_ENDPOINT || '/api';
}
```

개발/운영 모두 기본값 `/api`를 사용하므로 프론트엔드 코드는 환경별 백엔드 URL을 직접 알 필요가 없다. 개발에서는 Vite proxy, 운영에서는 nginx proxy가 실제 백엔드로 전달한다.

### 11.3 상태 저장소 분리

| Store | 파일 | 상태 | 용도 |
| --- | --- | --- | --- |
| Chat Store | `stores/chatStore.ts` | `currentThread`, `messages`, `streamingState`, `connection` | 일반 채팅 UI 상태 |
| Teams Store | `stores/teamsStore.ts` | `patterns`, `selectedPattern`, `teamsMessages`, `threadId` | Agent Teams UI 상태 |
| Theme Store/Hook | `hooks/useTheme.ts`, `types/theme.ts` | 현재 테마 | 채팅 테마 선택 |

## 12. 프론트엔드 코드 레벨 매핑

### 12.1 일반 채팅 전송

`useChat.sendMessage()`는 메시지 생성, 최신 store snapshot 확보, AG-UI message 변환, 첨부 metadata 변환, SSE 이벤트별 상태 업데이트까지 담당한다.

```
const priorMessages = useChatStore.getState().messages;
addMessage(userMessage);

const aguiMessages = [...priorMessages, userMessage]
  .filter((m) => m.role === 'user' || m.role === 'assistant')
  .map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
  }));
```

#### 이벤트별 UI 상태 변경

| SSE 이벤트 | `useChat` 처리 | UI 효과 |
| --- | --- | --- |
| `RUN_STARTED` | `isStreaming=true`, buffer 초기화 | 스트리밍 응답 버블 준비 |
| `TEXT_MESSAGE_START` | `assistantContent=""` | assistant 응답 누적 시작 |
| `TEXT_MESSAGE_CONTENT` | delta를 `assistantContent`와 streaming buffer에 누적 | 실시간 토큰 렌더링 |
| `TEXT_MESSAGE_END` | assistant 메시지를 `messages`에 commit | 완성 메시지로 전환 |
| `RUN_FINISHED` | streaming state 정리 | 입력 가능 상태 복구 |
| `RUN_ERROR` | logger 기록, 누적 content 초기화 | 오류 상태 표시 가능 |

### 12.2 AGUIClient

`AGUIClient.sendMessage()`는 fetch 요청과 SSE stream 처리를 담당한다. 요청마다 correlation id를 생성하고 `X-Correlation-ID` header로 전달한다.

```
const response = await fetch(`${this.baseUrl}/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Correlation-ID': correlationId,
  },
  body: JSON.stringify(request),
});
```

stream이 닫혔는데 `RUN_FINISHED`가 수신되지 않으면 protocol violation으로 보고 caller에 `ERROR` 이벤트를 전달한다.

### 12.3 Teams Hook

`useTeams()`는 mount 시 `/v1/patterns`를 호출해 패턴 목록을 가져오고, 사용자가 실행하면 `/v1/teams/stream`을 직접 읽어 이벤트별로 store를 갱신한다.

```
fetch(`${baseUrl}/v1/patterns`)
  .then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  })
  .then((data: unknown) => {
    if (Array.isArray(data)) {
      setPatterns(data);
    }
  });
```

### 12.4 업로드 클라이언트

`fileUploadService.uploadFile()`는 progress event가 필요한 이유로 `XMLHttpRequest`를 사용한다.

```
xhr.upload.addEventListener('progress', (event) => {
  if (event.lengthComputable && onProgress) {
    const percent = Math.round((event.loaded / event.total) * 100);
    onProgress(percent);
  }
});
```

## 13. 데이터 모델 및 이벤트 스키마

### 13.1 백엔드 Pydantic 모델

| 모델 | 주요 필드 | 검증/제약 |
| --- | --- | --- |
| `FleetRequest` | `items: list[FleetItem]`, `callback_url` | `min_length=1`, `max_length=20` |
| `InfiniteSessionRequest` | `prompt`, `iterations`, `system_message` | `iterations`: 1~10 |
| `FileAttachment` | `blob_name`, `original_filename`, `content_type`, `size_bytes` | `size_bytes`: 1~10,485,760 |
| `TeamsRequest` | `pattern_id`, `prompt`, `max_rounds`, `thread_id`, `attachments` | `max_rounds`: 1~10 |
| `JobStatusResponse` | `job_id`, `status`, `result`, `results`, `error` | 작업 상태 조회 응답 |

### 13.2 프론트엔드 TypeScript 타입

```
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  threadId: string;
  toolCalls?: ToolCall[];
  metadata?: MessageMetadata;
  attachments?: FileAttachment[];
}
```

```
export interface FileAttachment {
  blobName: string;
  originalFilename: string;
  contentType: string;
  sizeBytes: number;
}
```

```
export interface TeamsEvent {
  type:
    | 'TEAMS_STARTED'
    | 'AGENT_STARTED'
    | 'AGENT_MESSAGE_DELTA'
    | 'AGENT_MESSAGE_END'
    | 'ROUND_COMPLETED'
    | 'TEAMS_FINISHED'
    | 'TEAMS_ERROR';
  agent_role?: string;
  round?: number;
  delta?: string;
  content?: string;
  pattern_id?: string;
  run_id?: string;
  converged?: boolean;
  summary?: string;
  message?: string;
}
```

### 13.3 저장 위치별 영속성

| 데이터 | 저장 위치 | 영속성 | 코드 |
| --- | --- | --- | --- |
| 채팅 메시지 | 브라우저 Zustand memory | 새로고침 시 소실 | `chatStore.ts` |
| Copilot 세션 | 백엔드 `SessionPool` + SDK resume | 프로세스/SDK 상태에 의존 | `state.py` |
| 비동기 job | 백엔드 `_jobs` dict | 프로세스 재시작 시 소실 | `jobs.py` |
| Teams history | 백엔드 `_teams_history` dict | 프로세스 재시작 시 소실 | `orchestrator.py` |
| 업로드 파일 | Azure Blob Storage | 영속 | `blob_storage.py` |

## 14. 배포/인프라 설계

### 14.1 Dockerfile.appservice

운영 이미지는 multi-stage build로 구성된다. frontend build stage에서 Vite 정적 산출물을 만들고, Python backend stage에서 uv로 Python 의존성을 설치한 뒤, final stage에서 nginx와 supervisor를 설정한다.

```
Stage 1: node:20-alpine
  WORKDIR /app/frontend
  npm ci
  VITE_AGUI_ENDPOINT=/api npm run build

Stage 2: python:3.12-slim
  install curl/gcc/nginx/supervisor
  copy uv
  uv sync --frozen --no-dev
  copy backend app

Final:
  copy frontend dist -> /usr/share/nginx/html
  nginx listens :8080
  /api/ -> http://127.0.0.1:5100/
  /health -> http://127.0.0.1:5100/health
  supervisor starts nginx and backend
```

### 14.2 nginx 경로 설계

| 외부 경로 | nginx 처리 | 백엔드 도달 경로 |
| --- | --- | --- |
| `/`, SPA route | `try_files $uri $uri/ /index.html` | 백엔드 미도달 |
| `/api/` | `proxy_pass http://127.0.0.1:5100/` | `/` |
| `/api/v1/files/upload` | `/api` prefix 제거 | `/v1/files/upload` |
| `/health` | backend health로 proxy | `/health` |

### 14.3 Terraform 리소스

| 모듈/리소스 | 역할 | 설계 포인트 |
| --- | --- | --- |
| `acr` | 컨테이너 이미지 저장소 | admin disabled, App Service managed identity에 AcrPull |
| `app-service-plan` | Linux App Service compute | 기본 SKU P1v3 |
| `app-service` | 웹 앱 런타임 | `WEBSITES_PORT=8080`, managed identity, VNet integration |
| `storage` | 업로드 Blob 저장 | public network off, shared key off 기본값 |
| `network` | VNet/subnet | App integration subnet과 private endpoint subnet 분리 |
| `log-analytics` | 로그/모니터링 | 기본 retention 30일 |

### 14.4 GitHub Actions

- `ci.yml`: Python 3.12, uv sync, ruff, pytest 실행
- `deploy.yml`: Azure OIDC 로그인, Docker build/push, App Service 배포, health check
- 이미지 tag는 commit SHA와 `latest`를 함께 사용한다.
- 정적 인프라 설정은 Terraform, secret 기반 설정은 deploy workflow가 담당한다.

## 15. 보안 설계

### 15.1 인증과 권한

| 대상 | 방식 | 코드/설정 |
| --- | --- | --- |
| GitHub Copilot SDK 로컬 인증 | GitHub CLI 인증 상태 사용 | `gh auth login`, `GITHUB_TOKEN` 미설정 가능 |
| GitHub Copilot SDK 운영 인증 | App Service env `GITHUB_TOKEN` | `deploy.yml`에서 `COPILOT_GITHUB_TOKEN` 주입 |
| Azure 배포 인증 | GitHub Actions OIDC | `azure/login@v2` |
| ACR pull | App Service managed identity | Terraform `AcrPull` role assignment |
| Blob 접근 | `DefaultAzureCredential` | managed identity/Entra ID 기반 |

### 15.2 권한 승인 정책

중요: 현재 Copilot session 생성 시 `PermissionHandler.approve_all`이 사용된다. 단, `available_tools=[]`로 도구 목록은 비워져 있다. 향후 외부 도구 실행을 활성화한다면 approve-all 정책은 반드시 재검토해야 한다.

### 15.3 업로드 방어

- 확장자와 MIME allow-list를 모두 검사한다.
- generic MIME은 확장자를 기준으로 보정한다.
- 파일 크기 10MB 제한과 빈 파일 거부가 있다.
- 파일명에서 경로 컴포넌트와 unsafe 문자를 제거한다.
- Blob name에 UUID prefix를 붙여 충돌을 방지한다.

## 16. 로깅/관측성

### 16.1 백엔드 로깅

`logging_utils.py`는 `copilot_api` logger를 만들고 stdout handler를 등록한다. `CorrelationFilter`가 log record에 `correlation_id`를 주입한다.

```
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get("")
        return True
```

### 16.2 프론트엔드 correlation

프론트엔드 `AGUIClient`는 요청마다 correlation id를 생성해 header에 추가한다. 현재 백엔드에서 이 header를 contextvar에 자동 연결하는 미들웨어는 별도로 보이지 않으므로, end-to-end correlation을 강화하려면 `X-Correlation-ID`를 읽어 `correlation_id.set(...)`하는 FastAPI 미들웨어 추가가 필요하다.

### 16.3 Azure Monitor

`observability.py`는 `APPLICATIONINSIGHTS_CONNECTION_STRING`이 있을 때만 `configure_azure_monitor()`를 호출한다. 환경 변수가 없으면 로컬 개발 모드로 no-op이다.

```
connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
if not connection_string:
    logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set; tracing disabled")
    return False

os.environ.setdefault("OTEL_SERVICE_NAME", "agentic-devops-starter")
configure_azure_monitor(connection_string=connection_string)
```

## 17. 제한 사항과 개선 후보

| 현재 설계 | 제한/리스크 | 개선 후보 |
| --- | --- | --- |
| `_jobs` in-memory dict | 재시작/scale-out 시 작업 상태 유실 | Azure Queue/Service Bus + Table/Cosmos DB |
| `_teams_history` in-memory dict | 인스턴스 간 팀 대화 이력 공유 불가 | Redis 또는 Cosmos DB 기반 shared history |
| 브라우저 memory 기반 chat store | 새로고침 시 메시지 유실 | localStorage persistence 또는 서버 저장 API |
| 첨부 파일 전체 내용을 prompt에 삽입 | 큰 파일/바이너리의 토큰 비용과 응답 품질 문제 | 텍스트 추출, 요약, chunking, RAG pipeline |
| `PermissionHandler.approve_all` | 향후 도구 활성화 시 과도한 권한 승인 가능 | 도구별 allow-list와 사용자 승인 flow |
| Terraform local state 예시 | 팀 협업 시 state 충돌 가능 | Azure Storage remote backend 구성 |
| Chat/Teams SSE parser 분리 | 중복 parsing 로직 유지보수 비용 | 공통 SSE parser utility로 통합 |

### 17.1 우선순위 높은 개선

1. 백엔드 correlation middleware 추가로 프론트엔드 `X-Correlation-ID`와 로그 연결
1. Job/Teams history 외부 저장소 도입으로 scale-out 대응
1. 파일 첨부 전처리 pipeline 추가로 prompt 크기와 품질 관리
1. Agent Teams 이벤트 contract를 OpenAPI 또는 별도 schema로 고정
1. Terraform remote backend와 운영 monitoring/alert rule 문서화

현재 구조의 장점: 단일 프로세스/단일 App Service 인스턴스 기준으로는 구성요소가 단순하고, 기능별 코드 책임이 비교적 명확하다. 실습/스타터 프로젝트로서 로컬 개발, 컨테이너 배포, Azure 인프라, GitHub Actions CI/CD까지 한 흐름으로 파악하기 좋다.
