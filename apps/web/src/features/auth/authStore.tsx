import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import { api, setTokenProvider, request, ApiError } from "@/lib/api";
import type { User, AuthState } from "./authContext";
import {
  AuthStateContext,
  AuthActionsContext,
  getStoredToken,
  storeToken,
  clearStoredToken,
} from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const mountedRef = useRef(true);
  const restoreAborterRef = useRef<AbortController | null>(null);
  const loginAborterRef = useRef<AbortController | null>(null);

  const [state, setState] = useState<AuthState>(() => {
    const token = getStoredToken();
    if (token) {
      setTokenProvider(getStoredToken);
    }
    return {
      token,
      user: null,
      isLoading: !!token,
      error: null,
    };
  });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      setTokenProvider(() => null);
      restoreAborterRef.current?.abort();
      loginAborterRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setState((prev) => ({ ...prev, isLoading: false }));
      return;
    }

    setTokenProvider(getStoredToken);

    const aborter = new AbortController();
    restoreAborterRef.current = aborter;

    api
      .get<User>("/api/me", { signal: aborter.signal })
      .then((user) => {
        if (!mountedRef.current) return;
        setState({ token, user, isLoading: false, error: null });
      })
      .catch((err) => {
        if (!mountedRef.current || aborter.signal.aborted) return;

        if (err instanceof ApiError && err.status === 401) {
          clearStoredToken();
          setTokenProvider(() => null);
          window.dispatchEvent(new CustomEvent("auth:expired"));
          setState({
            token: null,
            user: null,
            isLoading: false,
            error: null,
          });
        } else {
          setState((prev) => ({
            ...prev,
            isLoading: false,
            error:
              "Unable to restore session. Please sign in again if the problem persists.",
          }));
        }
      });

    return () => {
      aborter.abort();
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    loginAborterRef.current?.abort();
    const aborter = new AbortController();
    loginAborterRef.current = aborter;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await request<{ access_token: string }>("/api/auth/login", {
        method: "POST",
        body: { email, password },
        noAuth: true,
        signal: aborter.signal,
      });

      if (aborter.signal.aborted) return;

      const token = result.access_token;
      storeToken(token);
      setTokenProvider(getStoredToken);

      const user = await api.get<User>("/api/me", {
        signal: aborter.signal,
      });

      if (aborter.signal.aborted || !mountedRef.current) return;

      setState({ token, user, isLoading: false, error: null });
    } catch (err) {
      if (aborter.signal.aborted || !mountedRef.current) return;

      const message =
        err instanceof ApiError
          ? err.message
          : "Login failed. Please try again.";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
    }
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setTokenProvider(() => null);
    setState({ token: null, user: null, isLoading: false, error: null });
  }, []);

  const stateValue = useMemo<AuthState>(
    () => ({
      token: state.token,
      user: state.user,
      isLoading: state.isLoading,
      error: state.error,
    }),
    [state.token, state.user, state.isLoading, state.error],
  );

  const actionsValue = useMemo(
    () => ({ login, logout }),
    [login, logout],
  );

  return (
    <AuthStateContext.Provider value={stateValue}>
      <AuthActionsContext.Provider value={actionsValue}>
        {children}
      </AuthActionsContext.Provider>
    </AuthStateContext.Provider>
  );
}
