import { api } from "@/lib/api";

export interface ConversationCreate {
  title?: string | null;
}

export interface ConversationResponse {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface ListConversationsParams {
  limit?: number;
  offset?: number;
}

export function createConversation(body: ConversationCreate): Promise<ConversationResponse> {
  return api.post<ConversationResponse>("/api/conversations", body);
}

export function fetchConversations(params?: ListConversationsParams): Promise<ConversationResponse[]> {
  return api.get<ConversationResponse[]>("/api/conversations", {
    params: {
      limit: params?.limit,
      offset: params?.offset,
    },
  });
}

export interface ListMessagesParams {
  limit?: number;
  offset?: number;
}

export function fetchMessages(
  conversationId: string,
  params?: ListMessagesParams,
): Promise<MessageResponse[]> {
  return api.get<MessageResponse[]>(
    `/api/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      params: {
        limit: params?.limit,
        offset: params?.offset,
      },
    },
  );
}
