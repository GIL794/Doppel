// Added in the local rebuild (not part of the recovered original code).
// Asks the backend once which capabilities are real versus simulated, so the
// UI labels exactly what is not connected - and only that.
import { useEffect, useState } from "react";

const ROOT = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");

const NONE = { payments_simulated: false, video_missing: false, email_missing: false, google_missing: false };

let cached = null;
export function fetchDemo() {
  if (!cached) {
    cached = fetch(`${ROOT}/api`)
      .then((r) => (r.ok ? r.json() : {}))
      .then((d) => {
        const c = d.capabilities || {};
        return {
          payments_simulated: c.payments === "mock",
          video_missing: c.ai_video === "none",
          email_missing: c.email === "not_configured",
          google_missing: c.google_auth === "unavailable",
        };
      })
      .catch(() => NONE);
  }
  return cached;
}

export function useDemo() {
  const [flags, setFlags] = useState(NONE);
  useEffect(() => {
    let live = true;
    fetchDemo().then((f) => live && setFlags(f));
    return () => { live = false; };
  }, []);
  flags.demo = flags.payments_simulated || flags.video_missing || flags.email_missing || flags.google_missing;
  return flags;
}
