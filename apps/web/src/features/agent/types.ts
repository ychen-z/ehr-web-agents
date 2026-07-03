export type AgentStatus = "idle" | "running" | "completed" | "failed";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  status: "sent" | "streaming" | "complete";
}

export interface StructuredResult {
  id: string;
  skill_id: string;
  tool_name: string;
  output: Record<string, unknown>;
  timestamp: number;
}

export interface AgentTimelineItem {
  id: string;
  eventType: SSEEventType;
  label: string;
  description: string;
  timestamp: number;
  status: "pending" | "running" | "completed" | "failed";
}

export interface ToolInvocationEvidence {
  runId: string | null;
  activeSkillName: string | null;
  skillId: string | null;
  toolName: string | null;
  startedAt: number | null;
  completedAt: number | null;
  outputKeys: string[];
}

export type SSEEventType =
  | "run_started"
  | "skill_selected"
  | "tool_started"
  | "tool_completed"
  | "model_delta"
  | "structured_result"
  | "checkpoint_reached"
  | "run_completed"
  | "run_failed"
  | "stream_closed";

export interface ActiveRun {
  runId: string;
  status: AgentStatus;
  assistantContent: string;
}

export type PanelView = "sidebar" | "results" | null;
