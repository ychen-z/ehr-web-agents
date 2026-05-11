import { api } from "@/lib/api";

export interface SkillResponse {
  id: string;
  skill_id: string;
  name: string;
  description: string | null;
  category: string | null;
  prompt_template: string | null;
  mock_tool_name: string | null;
  owner_user_id: string | null;
  visibility: "private" | "shared";
  source: "system" | "user";
  installed: boolean;
}

export interface SkillCreateRequest {
  skill_id: string;
  name: string;
  description?: string | null;
  category?: string | null;
  prompt_template?: string | null;
  mock_tool_name: string;
  visibility?: "private" | "shared";
}

export type SkillUpdateRequest = Partial<Omit<SkillCreateRequest, "skill_id">>;

export interface InstallResponse {
  skill_id: string;
  installed: boolean;
}

export function fetchSkills(): Promise<SkillResponse[]> {
  return api.get<SkillResponse[]>("/api/skills");
}

export function installSkill(skillId: string): Promise<InstallResponse> {
  return api.post<InstallResponse>(`/api/skills/${encodeURIComponent(skillId)}/install`);
}

export function uninstallSkill(skillId: string): Promise<InstallResponse> {
  return api.delete<InstallResponse>(`/api/skills/${encodeURIComponent(skillId)}/install`);
}

export function createSkill(body: SkillCreateRequest): Promise<SkillResponse> {
  return api.post<SkillResponse>("/api/skills", body);
}

export function updateSkill(skillId: string, body: SkillUpdateRequest): Promise<SkillResponse> {
  return api.patch<SkillResponse>(`/api/skills/${encodeURIComponent(skillId)}`, body);
}

export function deleteSkill(skillId: string): Promise<void> {
  return api.delete<void>(`/api/skills/${encodeURIComponent(skillId)}`);
}
