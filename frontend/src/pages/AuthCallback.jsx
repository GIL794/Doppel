import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const sessionId = new URLSearchParams(location.hash.slice(1)).get("session_id");
    const target = location.pathname && location.pathname !== "/login" ? location.pathname : "/dashboard";
    api
      .post("/auth/google/session", { session_id: sessionId })
      .then(({ data }) => {
        setUser(data);
        window.history.replaceState(null, "", target);
        navigate(target, { replace: true, state: { user: data } });
      })
      .catch(() => {
        toast.error("Google sign-in failed. Please try again.");
        navigate("/login", { replace: true });
      });
  }, [location, navigate, setUser]);

  return null;
}
