import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { authApi } from "../api/authApi";
import { handleMicrosoftRedirect } from "../utils/microsoftAuth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  const clearAuthError = useCallback(() => {
    setAuthError("");
  }, []);

  useEffect(() => {
    const initialize = async () => {
      // --- Microsoft OAuth redirect handling ---
      // handleRedirectPromise() is called on every app load.
      // If returning from Microsoft loginRedirect, it processes the response.
      try {
        const microsoftTokens = await handleMicrosoftRedirect();
        if (microsoftTokens) {
          try {
            const result = await authApi.microsoftLogin(microsoftTokens);
            setUser(result.user);
            setAuthError("");
          } catch (error) {
            setUser(null);
            setAuthError(error.message || "Microsoft sign-in failed.");
          } finally {
            setLoading(false);
          }
          return;
        }
      } catch (error) {
        // MSAL redirect processing failed
        setAuthError(error.message || "Failed to process Microsoft sign-in.");
      }

      // --- Normal session restoration via HttpOnly cookie ---
      try {
        const currentUser = await authApi.me();
        setUser(currentUser);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initialize();
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authApi.me();
      setUser(currentUser);
      return currentUser;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  const login = useCallback(async (credentials) => {
    const result = await authApi.login(credentials);
    setUser(result.user);
    setAuthError("");
    return result.user;
  }, []);

  const loginMicrosoft = useCallback(async (microsoftTokens) => {
    const result = await authApi.microsoftLogin(microsoftTokens);
    setUser(result.user);
    setAuthError("");
    return result.user;
  }, []);

  const register = useCallback((details) => authApi.register(details), []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setAuthError("");
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      authError,
      clearAuthError,
      isAuthenticated: Boolean(user),
      login,
      loginMicrosoft,
      register,
      logout,
      refreshUser,
    }),
    [user, loading, authError, clearAuthError, login, loginMicrosoft, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
