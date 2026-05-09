import { api } from "@/lib/api";

export interface RunCreate {
  skill_id: string;
  user_message: string;
  conversation_id?: string | null;
  model_provider_id?: string | null;
}

export interface RunResponse {
  id: string;
  conversation_id: string | null;
  user_id: string;
  skill_id: string;
  model_provider_id: string | null;
  status: string;
  structured_output: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export function createRun(body: RunCreate): Promise<RunResponse> {
  return api.post<RunResponse>("/api/agent/runs", body);
}

export function fetchRun(runId: string): Promise<RunResponse> {
  return api.get<RunResponse>(`/api/agent/runs/${encodeURIComponent(runId)}`);
}
