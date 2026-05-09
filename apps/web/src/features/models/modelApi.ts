import { api } from "@/lib/api";

export interface ModelConfigResponse {
  provider_id: string;
  display_name: string;
  default_model_name: string;
  configured: boolean;
  enabled: boolean;
}

export function fetchModels(): Promise<ModelConfigResponse[]> {
  return api.get<ModelConfigResponse[]>("/api/models");
}
