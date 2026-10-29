import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, API } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  // null = checking, false = signed out, object = user
  const [user, setUser] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      try {
        const { data } = await api.post("/auth/refresh");
        setUser(data);
      } catch {
        setUser(false);
      }
    }
  }, []);

  useEffect(() => {
    // Returning from Google OAuth: AuthCallback exchanges the session first.
    if (window.location.hash?.includes("session_id=")) {
      setUser(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const logout = async () => {
    await api.post("/auth/logout");
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, checkAuth, logout }}>{children}</AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export const startGoogleLogin = (next = "/dashboard") => {
  // Standard Google OAuth via the rebuilt backend. Off unless the owner
  // configures a Google OAuth client; the backend then bounces back to
  // /login?google=unavailable. The original's Emergent-hosted auth is gone.
  window.location.href = `${API}/auth/google/login?next=${encodeURIComponent(next)}`;
};
