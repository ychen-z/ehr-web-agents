import { API_BASE_URL } from "./api";

export interface RunEventData {
  run_id?: string;
  skill_id?: string;
  name?: string;
  tool_name?: string;
  output?: unknown;
  content?: string;
  error?: string;
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
 * SSE TOKEN-IN-QUERY TRADEOFF:
 * ==============================
 * Native EventSource cannot set custom HTTP headers (no Authorization header
 * possible). We pass the auth token as a `token` query parameter, which the
 * backend validates as a JWT. This exposes the token in browser history and
 * server access logs.
 *
 * TODO: Replace with a short-lived, scoped SSE token (e.g. single-run,
 * time-limited) once the backend supports it. This would limit the blast
 * radius if the URL leaks.
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
