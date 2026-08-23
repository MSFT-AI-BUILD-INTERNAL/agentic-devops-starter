# Agentic DevOps Starter 소프트웨어 설계 문서

현재 코드베이스 기준의 상세 설계 문서이다. FastAPI 백엔드, GitHub Copilot SDK 세션, Azure AI Foundry BYOK 라우팅, AG-UI 스타일 SSE 스트리밍, React/Vite 프론트엔드, Azure App Service 배포 인프라를 코드 레벨 구성요소와 런타임 흐름 중심으로 설명한다.

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
11. [Tool Calling 및 원격 MCP 클라이언트](#105-tool-calling-및-원격-mcp-클라이언트)
12. [프론트엔드 상세 설계](#11-프론트엔드-상세-설계)
12. [프론트엔드 코드 레벨 매핑](#12-프론트엔드-코드-레벨-매핑)
13. [데이터 모델 및 이벤트 스키마](#13-데이터-모델-및-이벤트-스키마)
14. [배포/인프라 설계](#14-배포인프라-설계)
15. [보안 설계](#15-보안-설계)
16. [로깅/관측성](#16-로깅관측성)
17. [제한 사항과 개선 후보](#17-제한-사항과-개선-후보)

## 1. 시스템 개요

Agentic DevOps Starter는 브라우저 기반 채팅 UI에서 입력한 메시지를 FastAPI 백엔드로 전달하고, 백엔드가 GitHub Copilot SDK 세션을 통해 응답을 생성한 뒤 SSE로 프론트엔드에 스트리밍하는 풀스택 애플리케이션이다. 채팅 UI의 모델 선택에 따라 기본 GitHub Copilot 세션 또는 Azure AI Foundry BYOK 세션으로 라우팅할 수 있으며, 단일 채팅뿐 아니라 파일 첨부, 병렬 프롬프트 실행, 반복 추론, 역할 기반 다중 에이전트 팀 실행을 지원한다.

| 영역 | 현재 구현 | 주요 코드 |
| --- | --- | --- |
| AI 런타임 | GitHub Copilot SDK의 `CopilotClient`, `CopilotSession` 사용. 일반 Copilot 세션과 Azure AI Foundry BYOK 세션을 분리 관리 | `app/agui_server.py`, `app/src/runtime/state.py` |
| API | FastAPI + StreamingResponse 기반 SSE. `/`는 기본 Copilot, `/v1/byok/foundry`는 Foundry BYOK | `app/src/api/routes.py` |
| 도구/MCP | `tools.py` 내장 도구와 선택적 원격 MCP 서버(`mcp_client.py`)를 통한 외부 도구 연동. `MCP_SERVER_URL` 환경변수로 활성화 | `app/src/runtime/tools.py`, `app/src/runtime/mcp_client.py` |
| 프론트엔드 | React 18, TypeScript, Vite, Zustand | `app/frontend/src/*` |
| 파일 저장 | Azure Blob Storage, `DefaultAzureCredential` | `app/src/storage/blob_storage.py`, `app/src/storage/file_validation.py` |
| 배포 | nginx + FastAPI + OTel Collector 단일 컨테이너를 Azure App Service에 배포 | `app/Dockerfile.appservice`, `infra/*` |

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
| - api/routes.py             |
| - SessionPool               |
| - FoundrySessionPool        |
| - Job Manager               |
| - Team Orchestrator         |
| - BlobStorageService        |
+------+----------+----------+
       |          |
       |          |                      |
       |          |                      +--------------------+
       v          v                                           v
+----------------------+  +----------------------+       +----------------------+
| GitHub Copilot SDK   |  | Azure AI Foundry     |       | Azure Blob Storage   |
| CopilotClient        |  | BYOK provider        |       | uploads container    |
| CopilotSession       |  | OpenAI-compatible    |       | private endpoint     |
+----------------------+  +----------------------+       +----------------------+
```

### 2.1 핵심 설계 원칙

- 프록시 경계 명확화: 백엔드에는 `/api` prefix를 두지 않고, Vite/nginx 계층에서만 사용한다.
- 세션 단위 대화 유지: `thread_id`별 Copilot SDK 세션을 유지해 멀티턴 대화 맥락을 보존한다.
- Provider 분리: 기본 GitHub Copilot과 Foundry BYOK는 별도 세션 풀과 endpoint를 사용해 인증·모델·세션 상태를 분리한다.
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
        load_skills()

        client = CopilotClient()
        await client.start()
        set_client(client)

        pool = SessionPool(idle_timeout=settings.session_timeout)
        set_session_pool(pool)
        foundry_pool = FoundrySessionPool(idle_timeout=settings.session_timeout)
        set_foundry_session_pool(foundry_pool)
        cleanup_tasks = [
            asyncio.create_task(_idle_cleanup_loop(pool)),
            asyncio.create_task(_idle_cleanup_loop(foundry_pool)),
        ]

        yield

        for cleanup_task in cleanup_tasks:
            cleanup_task.cancel()
        await foundry_pool.shutdown()
        await pool.shutdown()
        await client.stop()
```

| 단계 | 코드 레벨 동작 | 설계 의도 |
| --- | --- | --- |
| 환경 로드 | `load_dotenv()`, `Settings` | 로컬 개발과 운영 환경 변수 사용 방식 통일 |
| Copilot client 시작 | `CopilotClient()`, `await client.start()` | 요청마다 client를 만들지 않고 앱 단위 singleton으로 재사용 |
| SessionPool 설정 | `set_session_pool(pool)` | 라우트에서 전역 accessor로 thread별 세션 접근 |
| FoundrySessionPool 설정 | `set_foundry_session_pool(foundry_pool)` | `/v1/byok/foundry` 라우트에서 Foundry BYOK 세션에 접근 |
| idle cleanup | 30초마다 일반/Foundry pool 각각 `cleanup_idle()` | 장시간 미사용 Copilot 및 BYOK 세션 정리 |
| 종료 처리 | `foundry_pool.shutdown()`, `pool.shutdown()`, `client.stop()` | 프로세스 종료 시 SDK subprocess와 세션 연결 정리 |

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

`CORS_ORIGINS` 환경 변수가 비어 있으면 기본값은 `http://localhost:5173`, `http://127.0.0.1:5173`이다. 현재 Vite dev server는 `8080`을 사용하므로 실제 개발은 프록시 경유가 기본 흐름이다. `allow_credentials=True`는 쿠키 기반 인증이 작동하기 위해 필수이다.

### 3.4 GitHub App OAuth 인증 플로우

#### 3.4.1 인증 개요

`app/src/api/auth.py`가 OAuth 인증 전체를 담당한다. FastAPI `SessionMiddleware`를 사용하지 않으며, 암호화된 쿠키와 인메모리 CSRF 상태 저장소만으로 구성된 경량 stateless 인증이다.

`agui_server.py` lifespan에서 `initialize_session_cipher()`를 가장 먼저 호출해 Fernet 및 CMAC 파생 키를 LRU 캐시에 사전 적재한다.

#### 3.4.2 암호화 메커니즘

| 용도 | 알고리즘 | 파생 방법 | 비밀 |
| --- | --- | --- | --- |
| 세션 쿠키 암호화/복호화 | Fernet (AES-128-CBC + HMAC-SHA256) | PBKDF2-HMAC-SHA256, 600,000 iterations, 정적 salt | `GITHUB_CLIENT_SECRET` |
| 사용자 네임스페이스 ID 생성 | AES-CMAC | PBKDF2-HMAC-SHA256, 600,000 iterations, 별도 정적 salt | `GITHUB_CLIENT_SECRET` |

두 파생 함수 모두 `@lru_cache`로 캐시되어 프로세스당 KDF는 한 번만 실행된다. `GITHUB_CLIENT_SECRET`을 교체하면 기존 세션이 모두 무효화된다.

#### 3.4.3 엔드-투-엔드 OAuth 플로우

```
[Browser]                    [FastAPI]                    [GitHub]

App.tsx mount
  GET /auth/session (with cookie) ------>
                              cookie 없음/만료 → 401
  <------ 401 ---------------
  window.location(/auth/login)
  GET /auth/login ----------->
                              create_oauth_state()
                              → stores {state: expiry} in _oauth_states (10 min)
                              → builds authorize URL (client_id, redirect_uri, state)
  <------ 307 redirect ------
                                                           GitHub consent page
                              (user approves GitHub App)
                              GET /auth/callback?code=...&state=...
  ------------------------------------------------>
                              verify_oauth_state(state)   (pop from dict, check expiry)
                              exchange_code(code) -------> POST /login/oauth/access_token
                                                <--------- {"access_token": "ghu_..."}
                              store_token(token) → Fernet-encrypt(ghu_...)
                              set_session_cookie(response, ciphertext)
                              → httponly; secure; samesite=lax; max_age=28800
  <------ 307 redirect to / + Set-Cookie --------

[Browser]                    [FastAPI]
  POST /api/ (with cookie) -->
                              get_user_token(request)
                              → Fernet-decrypt(cookie, ttl=28800) → "ghu_..."
                              get_user_session_id()
                              → AES-CMAC("ghu_...") → opaque user namespace ID
                              get_user_isolation_namespace(session_id, X-Isolation-Session-ID)
                              → AES-CMAC("namespace:client_isolation") → session pool key
                              SessionPool.get_or_create(thread_key, github_token=ghu_...)
```

#### 3.4.4 세션 쿠키 속성

| 속성 | 값 | 설계 의도 |
| --- | --- | --- |
| 쿠키 이름 | `github_oauth_session` | 고정 상수 (`SESSION_COOKIE`) |
| `httponly` | `True` | JavaScript에서 쿠키 접근 차단 |
| `secure` | `True` | HTTPS 전송만 허용 |
| `samesite` | `lax` | CSRF 1차 방어 |
| `max_age` | `28800` (8시간) | Fernet TTL과 동일; 만료 시 자동 복호화 실패 → 401 |
| 내용 | Fernet-encrypted GitHub user access token | 토큰 원문은 서버 RAM에만 존재 |

#### 3.4.5 CSRF 보호

`_oauth_states` dict에 단일 사용(pop) 방식으로 state 토큰을 저장한다. 각 state 토큰은 `secrets.token_urlsafe(32)`로 생성되며 10분 후 만료된다. `verify_oauth_state()`는 dict에서 pop해 검증하므로 재사용이 불가능하다.

**한계**: `_oauth_states`는 인메모리 딕셔너리이므로 멀티 프로세스/멀티 인스턴스 배포에서 인스턴스 간 state 공유가 안 된다. 수평 확장 시 Redis 등 외부 상태 저장소가 필요하다.

#### 3.4.6 인증 적용 범위

| 엔드포인트 | 인증 |
| --- | --- |
| `POST /` | `get_user_token(request)` 직접 호출 → 쿠키 없으면 HTTP 401 |
| `POST /v1/byok/foundry` | OAuth 미적용; `github_token=None`으로 FoundrySessionPool 사용 |
| `/auth/*`, `/health`, `/v1/*` (채팅 제외) | 라우트 레벨 인증 없음 |

인증은 FastAPI `Depends()`가 아닌 라우트 핸들러 내부 직접 함수 호출로 구현된다.

## 4. 백엔드 코드 레벨 매핑

### 4.1 모듈별 책임

| 파일 | 핵심 함수/클래스 | 책임 |
| --- | --- | --- |
| `app/agui_server.py` | `create_app()`, `_idle_cleanup_loop()` | FastAPI 앱 생성, CopilotClient lifecycle, 미들웨어, CORS, router 등록 |
| `app/src/api/routes.py` | `agent_endpoint()`, `foundry_byok_endpoint()`, `upload_file()`, `teams_stream()` | HTTP 라우트와 SSE 응답 구성 |
| `app/src/api/auth.py` | `github_login()`, `github_callback()`, `get_user_session_id()`, `store_token()` | GitHub App OAuth 2.0 플로우 (`/auth/*` 라우트), session cookie 발급 |
| `app/src/runtime/state.py` | `SessionPool`, `FoundrySessionPool`, `get_client()`, `get_session_pool()`, `get_foundry_session_pool()` | CopilotClient singleton 및 thread별 CopilotSession 관리 |
| `app/src/runtime/jobs.py` | `create_job()`, `run_fleet()`, `run_infinite_session()` | 메모리 기반 비동기 작업 관리 |
| `app/src/runtime/tools.py` | 내장 도구 구현 | Copilot SDK에 등록되는 built-in 도구들. 파일 탐색, 코드 실행 등 |
| `app/src/runtime/mcp_client.py` | `MCPClient`, `get_mcp_tools()` | `MCP_SERVER_URL`이 설정된 경우 원격 MCP 서버에서 도구 목록을 조회해 `/v1/mcp/tools`로 제공 |
| `app/src/runtime/isolation.py` | `normalize_isolation_session_id()` | `X-Isolation-Session-ID` 헤더 기반 런타임 상태와 파일 접근 스코핑 |
| `app/src/teams/orchestrator.py` | `run_teams()`, `_stream_agent()`, flow runner들 | 다중 역할 Copilot session 오케스트레이션 |
| `app/src/teams/patterns.py` | `Pattern`, `AgentRole`, `PATTERNS` | Agent Team 패턴과 역할별 system prompt 정의 (YAML 기반) |
| `app/src/runtime/skills.py` | `load_skills()`, `get_skill_directories()`, `get_disabled_skills()` | SKILL.md 디렉터리 디스커버리 및 SDK 전달용 경로 해석 |
| `app/src/storage/blob_storage.py` | `BlobStorageService`, `get_blob_service()` | Azure Blob upload/download |
| `app/src/storage/file_validation.py` | `validate_file_type()`, `validate_file_size()`, `generate_blob_name()` | 파일 확장자/MIME/크기/파일명 sanitization |

### 4.2 API 라우트와 함수 매핑

| HTTP | 라우트 | 함수 | 반환 타입/형태 | 주요 의존성 |
| --- | --- | --- | --- | --- |
| GET | `/health` | `health_check()` | `{"status": "healthy"}` | 없음 |
| POST | `/` | `agent_endpoint()` | `StreamingResponse(text/event-stream)` | `SessionPool`, `CopilotSession`, `_resolve_attachments()` |
| POST | `/v1/byok/foundry` | `foundry_byok_endpoint()` | `StreamingResponse(text/event-stream)` | `FoundrySessionPool`, Foundry provider config, `_resolve_attachments()` |
| GET | `/auth/login` | `github_login()` | `RedirectResponse` → GitHub OAuth | `settings.github_client_id`, `create_oauth_state()` |
| GET | `/auth/callback` | `github_callback()` | `RedirectResponse` → `/` | `verify_oauth_state()`, `exchange_code()`, `store_token()` |
| GET | `/auth/session` | `auth_session()` | `{"authenticated": bool, ...}` | `get_user_session_id()`, `get_user_token()` |
| POST | `/auth/logout` | `auth_logout()` | `204 No Content` | `SESSION_COOKIE` 삭제 |
| POST | `/v1/files/upload` | `upload_file()` | `UploadResult` 또는 error JSON | `file_validation`, `BlobStorageService` |
| DELETE | `/v1/threads/{thread_id}` | `delete_thread()` | `{"status": "deleted"}` | `SessionPool.disconnect()`, `FoundrySessionPool.disconnect()` |
| POST | `/v1/threads/{thread_id}/abort` | `abort_thread()` | `{"status": "aborted"}` | 진행 중인 채팅/팀 생성 취소 |
| POST | `/v1/fleet` | `fleet_endpoint()` | 202 + `{"job_id": ...}` | `create_job()`, `run_fleet()` |
| POST | `/v1/infinite-session` | `infinite_session_endpoint()` | 202 + `{"job_id": ...}` | `create_job()`, `run_infinite_session()` |
| GET | `/v1/patterns` | `list_patterns()` | `list[PatternInfo]` | `PATTERNS` |
| POST | `/v1/teams/stream` | `teams_stream()` | `StreamingResponse(text/event-stream)` | `run_teams()`, `_resolve_attachments()` |
| GET | `/v1/jobs/{job_id}` | `job_status_endpoint()` | `JobStatusResponse` | `get_job()` |
| GET | `/v1/mcp/tools` | `list_mcp_tools()` | `list[MCPToolResponse]` | `MCPClient`, `MCP_SERVER_URL` |

## 5. 일반 채팅 스트리밍 흐름

### 5.1 서버 내부 알고리즘

`agent_endpoint()`와 `foundry_byok_endpoint()`는 요청 body에서 thread/run/message/attachment 정보를 추출한 뒤, 공통 `_chat_streaming_response()` helper로 `StreamingResponse`를 반환한다. 두 endpoint의 SSE wire format은 동일하며, 차이는 사용할 session pool이다.

| Endpoint | Pool | Provider |
| --- | --- | --- |
| `/` | `SessionPool` | 기본 GitHub Copilot |
| `/v1/byok/foundry` | `FoundrySessionPool` | Azure AI Foundry BYOK provider |

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
   | POST /api/ or           |                                  |
   | /api/v1/byok/foundry    |                                  |
   |------------------------>|                                  |
   |                         | select SessionPool or            |
   |                         | FoundrySessionPool               |
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

### 6.0 세션 라우팅 패턴

일반 채팅의 세션 라우팅 키는 인증 사용자 ID가 아니라 클라이언트가 전달하는 `thread_id`이다. 프론트엔드는 새 대화를 시작할 때 UUID 기반 thread를 만들고 같은 대화의 후속 요청에 동일 `thread_id`를 보낸다. 백엔드는 이 값을 그대로 Copilot SDK `session_id`로 사용하므로, 서로 다른 브라우저/사용자가 서로 다른 `thread_id`를 사용하면 같은 서버 프로세스 안에서 독립 Copilot 세션으로 동시에 처리된다.

| 항목 | 설계 |
| --- | --- |
| 라우팅 키 | `thread_id` |
| SDK 매핑 | `thread_id` → `CopilotSession`, 신규 생성 시 `session_id=thread_id` |
| 동시 사용 모델 | 여러 `thread_id`를 `SessionPool`이 병렬 보관하고, thread별 lock은 세션 조회/생성/해제 경합을 보호 |
| 사용자별 분리 | 별도 `user_id` 네임스페이스는 두지 않음. 정상 UI 흐름에서는 각 브라우저 대화가 고유 `thread_id`를 생성해 분리 |
| 컨텍스트 유지 | 서버는 최신 user prompt만 전송하고, 이전 대화 맥락은 동일 Copilot SDK 세션이 유지 |

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

### 6.2 Foundry BYOK 세션 풀

`FoundrySessionPool`은 기본 `SessionPool`과 별도 dictionary/lock을 사용해 Azure AI Foundry BYOK 세션을 분리한다. 신규 세션 생성 시 SDK `session_id`에는 `foundry-{thread_id}` prefix를 붙여 일반 Copilot 세션과 충돌하지 않게 한다.

| 항목 | 설계 |
| --- | --- |
| 라우트 | `/v1/byok/foundry` |
| 세션 ID | `foundry-{thread_id}` |
| 모델 | `AZURE_AI_MODEL_DEPLOYMENT_NAME` |
| provider type | `openai` |
| base URL | `AZURE_AI_PROJECT_ENDPOINT`를 `/openai/v1/` 형식으로 정규화 |
| wire API | `FOUNDRY_WIRE_API`, 허용값은 `responses` 또는 `completions` |
| 인증 | `FOUNDRY_AUTH_MODE=auto|api_key|azure_identity` |

Foundry provider는 `app/src/runtime/state.py`의 `_build_foundry_provider()`에서 구성한다. `api_key` 모드에서는 `FOUNDRY_API_KEY` 또는 `AZURE_OPENAI_API_KEY`를 사용하고, `azure_identity` 모드에서는 `DefaultAzureCredential`로 `https://cognitiveservices.azure.com/.default` scope의 bearer token을 가져온다. `auto` 모드는 API key가 있으면 `api_key`, 없으면 `azure_identity`로 해석한다.

Azure Identity 토큰은 만료 5분 전부터 세션을 재생성하도록 `_token_expires_on`에 만료 시각을 보관한다. 이를 통해 만료 직전 bearer token을 가진 기존 Foundry 세션을 계속 재사용하지 않는다.

필수 설정이 누락되거나 `FOUNDRY_WIRE_API`/`FOUNDRY_AUTH_MODE` 값이 허용 범위를 벗어나면 세션 생성 전에 `RuntimeError("Foundry BYOK is not configured: ...")`가 발생하고, 라우트는 SSE `RUN_ERROR`로 사용자에게 구성 오류를 전달한다.

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

`src.runtime.skills.load_skills()`는 앱 시작 시 한 번 실행되어 스킬 디렉터리를 탐색·캐싱한다. 애플리케이션은 **스킬 레지스트리가 아니다** — 스킬을 API로 나열하거나 서빙하지 않으며, SDK가 스캔할 파일시스템 경로만 결정한다.

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

## 10.5. Tool Calling 및 원격 MCP 클라이언트

### 10.5.1 개요

백엔드는 Copilot SDK 세션에 등록되는 **내장 도구**(`tools.py`)와 선택적으로 연결되는 **원격 MCP 서버**(`mcp_client.py`) 두 가지 경로로 도구를 제공한다. 도구 정책은 `COPILOT_API_ALLOWED_TOOLS`(허용 목록)와 `COPILOT_API_EXCLUDED_TOOLS`(차단 목록) 환경 변수로 제어한다.

| 컴포넌트 | 파일 | 역할 |
| --- | --- | --- |
| 내장 도구 | `app/src/runtime/tools.py` | 앱과 함께 배포되는 built-in 도구 구현 |
| MCP 클라이언트 | `app/src/runtime/mcp_client.py` | `MCP_SERVER_URL`이 설정된 경우 원격 MCP 서버에 연결해 도구 목록 조회 |
| 도구 목록 API | `GET /v1/mcp/tools` | 원격 MCP 서버에서 조회한 도구 목록을 `list[MCPToolResponse]`로 반환 |

### 10.5.2 도구 정책

| 환경 변수 | 타입 | 설명 |
| --- | --- | --- |
| `COPILOT_API_ALLOWED_TOOLS` | 쉼표 구분 문자열 | 설정 시 허용 목록 모드로 전환. 명시된 도구 이름만 허용 |
| `COPILOT_API_EXCLUDED_TOOLS` | 쉼표 구분 문자열 | 차단 목록. `ALLOWED_TOOLS`가 없을 때 유효 |
| `COPILOT_API_TOOL_TIMEOUT` | 초 단위 정수 | 개별 도구 호출 타임아웃 |
| `THIRDPARTY_GITHUB_PAT` | PAT 문자열 | `fetch_github_zen` 데모 도구가 고정된 `https://api.github.com/zen`을 호출할 때 `Authorization` 헤더로 첨부되는 PAT. Copilot SDK 세션용 GitHub Apps OAuth와 무관 |

### 10.5.3 원격 MCP 서버 연동

`MCP_SERVER_URL` 환경 변수에 원격 MCP 서버 URL을 설정하면 `mcp_client.py`가 해당 서버에서 도구 목록을 가져온다. MCP 서버가 없으면 내장 도구만 사용하고, `/v1/mcp/tools`는 빈 목록을 반환한다.

```
MCP_SERVER_URL 설정됨
  -> MCPClient 초기화
  -> GET /v1/mcp/tools 호출 시 MCP 서버 도구 목록 조회
  -> list[MCPToolResponse] 반환

MCP_SERVER_URL 미설정
  -> /v1/mcp/tools → []
  -> 내장 도구만 Copilot SDK 세션에 등록
```

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

채팅 전송 endpoint는 모델 provider 선택에 따라 `AGUIClient`에서 한 번 더 분기한다. `github-copilot`은 `/api/`로, `foundry`는 `/api/v1/byok/foundry`로 전송된다.

| ModelProvider | UI label | Backend endpoint |
| --- | --- | --- |
| `github-copilot` | GitHub Copilot | `/` |
| `foundry` | Microsoft Foundry | `/v1/byok/foundry` |

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

`AGUIClient.sendMessage()`는 fetch 요청과 SSE stream 처리를 담당한다. 요청마다 correlation id를 생성하고 `X-Correlation-ID` header로 전달하며, `modelProvider` 값에 따라 기본 Copilot endpoint 또는 Foundry BYOK endpoint를 선택한다.

```
const endpoint = modelProvider === 'foundry' ? '/v1/byok/foundry' : '/';
const response = await fetch(this.buildUrl(endpoint), {
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
  copy OTel Collector binary
  nginx listens :8080
  /api/ -> http://127.0.0.1:5100/
  /health -> http://127.0.0.1:5100/health
  supervisor starts nginx, backend (uvicorn :5100), otel-collector (:4318)
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
- `deploy.yml`: 3개 job으로 구성
  - `build-and-push`: Azure OIDC 로그인, Docker Buildx build/push to ACR
  - `deploy`: App Service 배포, secret 주입, health check (5회 재시도)
  - `playwright-test`: 배포 후 E2E 테스트 실행 (`npm run test:e2e`), `PLAYWRIGHT_GITHUB_TOKEN`/`PLAYWRIGHT_GITHUB_CLIENT_SECRET` 필요
- 이미지 tag는 commit SHA와 `latest`를 함께 사용한다.
- 정적 인프라 설정은 Terraform, secret 기반 설정은 deploy workflow가 담당한다.

## 15. 보안 설계

### 15.1 인증과 권한

#### 사용자 인증 — GitHub App OAuth

| 단계 | 대상 | 방식 | 코드/설정 |
| --- | --- | --- | --- |
| 세션 탐지 | 브라우저 → FastAPI | `GET /auth/session` + 쿠키 → 401 → `/auth/login` 리다이렉트 | `App.tsx` (mount 시 1회 probe) |
| OAuth 시작 | FastAPI → GitHub | CSRF state 생성 후 GitHub authorization URL로 307 redirect | `GET /auth/login`, `create_oauth_state()` |
| 콜백 처리 | GitHub → FastAPI | state 검증 → code 교환 → 토큰 암호화 → 쿠키 발급 | `GET /auth/callback`, `exchange_code()`, `store_token()` |
| 요청별 인증 | 브라우저 → FastAPI | `github_oauth_session` 쿠키 복호화 → GitHub user token 획득 | `get_user_token(request)` |
| 사용자 네임스페이스 | FastAPI 내부 | AES-CMAC(token) → 불투명 사용자 ID → 세션 풀 키 | `get_user_session_id()`, `get_user_isolation_namespace()` |
| 로그아웃 | 브라우저 → FastAPI | 쿠키 삭제 (GitHub 서버 토큰 폐기 없음) | `POST /auth/logout` |

쿠키 속성: `name=github_oauth_session; httponly; secure; samesite=lax; max_age=28800(8h)`.

#### 인프라 / 서비스 인증

| 대상 | 방식 | 코드/설정 |
| --- | --- | --- |
| GitHub Copilot SDK (로컬) | GitHub CLI 인증 상태 | `gh auth login` |
| GitHub Copilot SDK (운영) | OAuth로 얻은 `ghu_...` 토큰을 CopilotSession에 전달 | `get_user_token()` → `SessionPool.get_or_create(github_token=...)` |
| Azure AI Foundry BYOK API key | `FOUNDRY_AUTH_MODE=api_key` | `FOUNDRY_API_KEY` 또는 `AZURE_OPENAI_API_KEY` |
| Azure AI Foundry BYOK Entra ID | `FOUNDRY_AUTH_MODE=azure_identity` 또는 `auto` | `DefaultAzureCredential`, scope `https://cognitiveservices.azure.com/.default` |
| Azure 배포 | GitHub Actions OIDC | `azure/login@v2` |
| ACR pull | App Service managed identity | Terraform `AcrPull` role assignment |
| Blob 접근 | `DefaultAzureCredential` | managed identity/Entra ID 기반 |

Foundry BYOK 설정은 `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `FOUNDRY_AUTH_MODE`, `FOUNDRY_API_KEY`, `FOUNDRY_WIRE_API`로 제어한다. `FOUNDRY_WIRE_API`는 SDK provider의 OpenAI-compatible wire protocol을 지정하며 현재 `responses`와 `completions`만 허용한다.

`POST /v1/byok/foundry`는 OAuth를 적용하지 않는다 (`github_token=None`으로 FoundrySessionPool에 전달).

#### Playwright E2E 인증 시뮬레이션

E2E 테스트(`e2e/global-setup.ts`)는 OAuth 브라우저 플로우를 우회하기 위해 `PLAYWRIGHT_GITHUB_CLIENT_SECRET`(= `COPILOT_APP_CLIENT_SECRET`)으로 동일한 PBKDF2+Fernet 암호화를 Node.js에서 재현해 유효한 세션 쿠키를 직접 생성한다. `PLAYWRIGHT_GITHUB_TOKEN`(GitHub PAT)이 쿠키에 담길 토큰 값으로 사용된다.

### 15.2 권한 승인 정책

중요: 현재 Copilot session 생성 시 `PermissionHandler.approve_all`이 사용된다. `tools.py` 내장 도구와 원격 MCP 도구가 등록된 경우 모든 실행 요청이 자동 승인된다. `COPILOT_API_ALLOWED_TOOLS` / `COPILOT_API_EXCLUDED_TOOLS`로 1차 필터링이 가능하지만, 런타임 승인 정책 자체는 approve-all이므로 프로덕션 배포에서는 허용 목록을 명시적으로 설정해야 한다.

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
| `_oauth_states` in-memory dict (CSRF) | 멀티 인스턴스 배포 시 인스턴스 간 state 공유 불가 → CSRF 검증 실패 가능 | Redis 또는 외부 KV 저장소 |
| `POST /auth/logout` 토큰 미폐기 | 로그아웃 후에도 GitHub에서 해당 user token이 살아 있음 | GitHub token revocation API 호출 추가 |
| OAuth 미적용 라우트 | `/v1/byok/foundry`, `/v1/files/upload`, `/v1/teams/stream` 등이 인증 없이 접근 가능 | 라우트별 `Depends(get_current_user)` 적용 |
| `_teams_history` in-memory dict | 인스턴스 간 팀 대화 이력 공유 불가 | Redis 또는 Cosmos DB 기반 shared history |
| 브라우저 memory 기반 chat store | 새로고침 시 메시지 유실 | localStorage persistence 또는 서버 저장 API |
| 첨부 파일 전체 내용을 prompt에 삽입 | 큰 파일/바이너리의 토큰 비용과 응답 품질 문제 | 텍스트 추출, 요약, chunking, RAG pipeline |
| `PermissionHandler.approve_all` | 내장 도구와 MCP 도구가 활성화된 경우 모든 도구 실행을 자동 승인함. `COPILOT_API_ALLOWED_TOOLS`/`COPILOT_API_EXCLUDED_TOOLS`로 1차 필터링하지만, 런타임 승인 정책은 여전히 approve-all | 도구별 allow-list와 사용자 승인 flow로 교체 |
| Terraform local state 예시 | 팀 협업 시 state 충돌 가능 | Azure Storage remote backend 구성 |
| Chat/Teams SSE parser 분리 | 중복 parsing 로직 유지보수 비용 | 공통 SSE parser utility로 통합 |

### 17.1 우선순위 높은 개선

1. 백엔드 correlation middleware 추가로 프론트엔드 `X-Correlation-ID`와 로그 연결
1. Job/Teams history 외부 저장소 도입으로 scale-out 대응
1. 파일 첨부 전처리 pipeline 추가로 prompt 크기와 품질 관리
1. Agent Teams 이벤트 contract를 OpenAPI 또는 별도 schema로 고정
1. Terraform remote backend와 운영 monitoring/alert rule 문서화

현재 구조의 장점: 단일 프로세스/단일 App Service 인스턴스 기준으로는 구성요소가 단순하고, 기능별 코드 책임이 비교적 명확하다. 실습/스타터 프로젝트로서 로컬 개발, 컨테이너 배포, Azure 인프라, GitHub Actions CI/CD까지 한 흐름으로 파악하기 좋다.
