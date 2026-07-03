import { API_BASE_URL } from "./api";

export interface RunEventData {
  run_id?: string;
  skill_id?: string;
  name?: string;
  tool_name?: string;
  output?: unknown;
  content?: string;
  error?: string;
  prompt?: string;
  options?: { label: string; value: string; description?: string }[];
  tool_output?: unknown;
  [key: string]: unknown;
}

export interface RunEventHandlers {
  onOpen?: (event: Event) => void;
  onRunStarted?: (data: RunEventData) => void;
  onSkillSelected?: (data: RunEventData) => void;
  onToolStarted?: (data: RunEventData) => void;
  onToolCompleted?: (data: RunEventData) => void;
  onModelDelta?: (data: RunEventData) => void;
  onStructuredResult?: (data: RunEventData) => void;
  onCheckpointReached?: (data: RunEventData) => void;
  onRunCompleted?: (data: RunEventData) => void;
  onRunFailed?: (data: RunEventData) => void;
  onStreamClosed?: (data: RunEventData) => void;
  onError?: (error: Event) => void;
}

export interface SSESubscription {
  close: () => void;
  readyState: () => number;
}

function add(
  entries: [string, (event: Event) => void][],
  type: string,
  handler: ((event: Event) => void) | null,
) {
  if (handler) entries.push([type, handler]);
}

function makeHandler(
  eventType: string,
  handler: ((data: RunEventData) => void) | undefined,
  onAfter?: () => void,
) {
  return handler
    ? (event: Event) => {
        const raw = (event as MessageEvent).data as string;
        try {
          handler(JSON.parse(raw) as RunEventData);
        } catch {
          console.warn(
            `[SSE] Failed to parse JSON data for event "${eventType}":`,
            raw.slice(0, 200),
          );
        } finally {
          onAfter?.();
        }
      }
    : null;
}

/*
 * SSE 查询参数传递 Token 的权衡：
 * ==============================
 * 原生 EventSource 无法设置自定义 HTTP 请求头（无法添加 Authorization 头）。
 * 因此我们将认证 token 作为 `token` 查询参数传递，后端会将其作为 JWT 进行验证。
 * 这会导致 token 暴露在浏览器历史记录和服务器访问日志中。
 *
 * TODO: 后端支持后，替换为短期、限定作用域的 SSE token（例如单次运行、
 * 限时有效），以减少 URL 泄露时的影响范围。
 */
export function subscribeToRunEvents(
  runId: string,
  token: string,
  handlers: RunEventHandlers,
): SSESubscription {
  const url = `${API_BASE_URL}/api/agent/runs/${encodeURIComponent(runId)}/events?token=${encodeURIComponent(token)}`;
  const eventSource = new EventSource(url);

  if (handlers.onOpen) {
    eventSource.addEventListener("open", handlers.onOpen);
  }

  const entries: [string, (event: Event) => void][] = [];
  const closeOnTerminalEvent = () => eventSource.close();
  add(entries, "run_started", makeHandler("run_started", handlers.onRunStarted));
  add(entries, "skill_selected", makeHandler("skill_selected", handlers.onSkillSelected));
  add(entries, "tool_started", makeHandler("tool_started", handlers.onToolStarted));
  add(entries, "tool_completed", makeHandler("tool_completed", handlers.onToolCompleted));
  add(entries, "model_delta", makeHandler("model_delta", handlers.onModelDelta));
  add(entries, "structured_result", makeHandler("structured_result", handlers.onStructuredResult));
  add(entries, "checkpoint_reached", makeHandler("checkpoint_reached", handlers.onCheckpointReached, closeOnTerminalEvent));
  add(entries, "run_completed", makeHandler("run_completed", handlers.onRunCompleted, closeOnTerminalEvent));
  add(entries, "run_failed", makeHandler("run_failed", handlers.onRunFailed, closeOnTerminalEvent));
  add(entries, "stream_closed", makeHandler("stream_closed", handlers.onStreamClosed, closeOnTerminalEvent));

  for (const [eventType, handler] of entries) {
    eventSource.addEventListener(eventType, handler);
  }

  if (handlers.onError) {
    eventSource.onerror = handlers.onError;
  }

  return {
    close: () => eventSource.close(),
    readyState: () => eventSource.readyState,
  };
}
