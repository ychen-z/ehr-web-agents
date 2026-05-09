import { api } from "@/lib/api";

export interface SkillResponse {
  id: string;
  skill_id: string;
  name: string;
  description: string | null;
  category: string | null;
  installed: boolean;
}

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
