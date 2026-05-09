import { useContext } from "react";
import { AuthStateContext, AuthActionsContext } from "./authContext";

export type { User } from "./authContext";

export function useAuth() {
  const state = useContext(AuthStateContext);
  const actions = useContext(AuthActionsContext);
  if (!state || !actions) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return { ...state, ...actions };
}
