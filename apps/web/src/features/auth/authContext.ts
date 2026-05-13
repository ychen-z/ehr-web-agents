import { createContext } from "react";

export interface User {
  id: string;
  email: string;
  role: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthStateContext = createContext<AuthState | null>(null);
export const AuthActionsContext = createContext<AuthActions | null>(null);

export const STORAGE_KEY = "hr-agent-token";

function safeStorage(): Storage | null {
  try {
    return sessionStorage;
  } catch {
    return null;
  }
}

export function getStoredToken(): string | null {
  const s = safeStorage();
  if (!s) return null;
  try {
    return s.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  const s = safeStorage();
  if (!s) return;
  try {
    s.setItem(STORAGE_KEY, token);
  } catch {
    // 存储被阻止或配额已满
  }
}

export function clearStoredToken(): void {
  const s = safeStorage();
  if (!s) return;
  try {
    s.removeItem(STORAGE_KEY);
  } catch {
    // 存储被阻止
  }
}
