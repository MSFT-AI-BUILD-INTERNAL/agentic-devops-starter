# AG-UI Server API Reference

HTTP/SSE API for the Agentic DevOps Starter backend. Chat requests stream responses using the [AG-UI SSE protocol](#sse-event-types).

> **PowerShell note**: `curl` in PowerShell is an alias for `Invoke-WebRequest`. Use `curl.exe` instead to invoke the real curl binary (shipped with Windows 10/11).

---

## Base URL

```
https://app-agentic-devops.azurewebsites.net
```

---

## Authentication

인증 구조, 자동화 방법(세션 토큰 헤더 전달 / GitHub Device Flow) 상세 내용은 [API_Auth.md](API_Auth.md)를 참고하세요.

| Endpoint | Auth required |
|---|---|
| `POST /` | GitHub 인증 토큰 (`Authorization: Bearer <session_token>`) |
| All other endpoints | 없음 |

---

## Chat Endpoints

Chat requests use the GitHub Copilot SDK and require GitHub authentication.

### POST /
GitHub Copilot SDK backend. GitHub authentication is required (`Authorization` header or session cookie).

#### Request body

```json
{
  "messages": [
    { "role": "user", "content": "Hello, what can you do?" }
  ],
  "thread_id": "test-thread-001",
  "run_id": "run-001",
  "attachments": []
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `messages` | `array` | Yes | 대화 히스토리. 최신 사용자 메시지만 SDK로 전달되고, 이전 턴은 서버가 `thread_id` 기준으로 관리합니다. |
| `thread_id` | `string` | No | 대화 세션 식별자. 생략 시 서버가 자동 생성. 멀티턴 대화에서는 동일한 값을 재사용하세요. |
| `run_id` | `string` | No | 이번 생성 요청의 식별자. `RUN_STARTED` / `RUN_FINISHED` 이벤트에 그대로 반환됩니다. |
| `attachments` | `array` | No | 파일 컨텍스트로 포함할 업로드된 blob 참조 목록. |

#### Response

`Content-Type: text/event-stream` — 줄 단위 SSE 스트림. [SSE Event Types](#sse-event-types) 참고.

---

## SSE Event Types

스트림의 각 줄은 `data: ` 접두사와 JSON 객체로 구성됩니다.

```
data: {"type": "RUN_STARTED", "thread_id": "...", "run_id": "..."}

data: {"type": "TEXT_MESSAGE_START", "message_id": "abc123"}

data: {"type": "TEXT_MESSAGE_CONTENT", "delta": "Hello! I can "}

data: {"type": "TEXT_MESSAGE_CONTENT", "delta": "help you with..."}

data: {"type": "TEXT_MESSAGE_END", "message_id": "abc123"}

data: {"type": "RUN_FINISHED", "thread_id": "...", "run_id": "..."}
```

| Event type | Description |
|---|---|
| `RUN_STARTED` | 생성 시작. `thread_id`, `run_id` 포함. |
| `TEXT_MESSAGE_START` | 어시스턴트 메시지 시작. `message_id` 포함. |
| `TEXT_MESSAGE_CONTENT` | 텍스트 청크. `delta` 포함. |
| `TEXT_MESSAGE_END` | 어시스턴트 메시지 완료. `message_id` 포함. |
| `RUN_FINISHED` | 생성 완료. 오류 발생 시에도 항상 전송됨. |
| `RUN_ERROR` | 오류 발생. `message` 포함. |

---

## curl Examples

### Chat (Device Flow 또는 세션 토큰)

```powershell
# PowerShell
curl.exe -N -X POST https://app-agentic-devops.azurewebsites.net/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer <session_token>" `
  -d '{"messages": [{"role": "user", "content": "Hello!"}], "thread_id": "test-thread-001", "run_id": "run-001"}'
```

```bash
# Linux
curl -N -X POST https://app-agentic-devops.azurewebsites.net/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}], "thread_id": "test-thread-001", "run_id": "run-001"}'
```

---

## Thread Management

### DELETE /v1/threads/{thread_id}
세션을 끊습니다. 세션 상태는 디스크에 보존되어 다음 요청에서 재개할 수 있습니다.

```powershell
# PowerShell
curl.exe -X DELETE https://app-agentic-devops.azurewebsites.net/v1/threads/test-thread-001
# → {"status": "deleted", "thread_id": "test-thread-001"}
```

```bash
# Linux
curl -X DELETE https://app-agentic-devops.azurewebsites.net/v1/threads/test-thread-001
```

### POST /v1/threads/{thread_id}/abort
세션을 끊지 않고 진행 중인 생성만 중단합니다.

```powershell
# PowerShell
curl.exe -X POST https://app-agentic-devops.azurewebsites.net/v1/threads/test-thread-001/abort
# → {"status": "aborted", ...} or {"status": "not_found", ...}
```

```bash
# Linux
curl -X POST https://app-agentic-devops.azurewebsites.net/v1/threads/test-thread-001/abort
```

---

## Architecture Note

Chat 엔드포인트는 [`src/runtime/state.py`](../app/src/runtime/state.py)의 `AISessionPool` 인터페이스를 통해 라우팅됩니다. 구체 구현체는 두 가지입니다:

| Pool | Endpoint | Provider |
|---|---|---|
| `SessionPool` | `POST /` | GitHub Copilot SDK |

새 AI 프로바이더 추가 시 `AISessionPool` Protocol의 4개 메서드만 구현하면 routes나 lifecycle 코드 수정이 필요 없습니다.
