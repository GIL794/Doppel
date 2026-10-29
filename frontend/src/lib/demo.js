// Added in the local rebuild (not part of the recovered original code).
// Asks the backend once which capabilities are real versus simulated, so the
// UI labels exactly what is not connected. Three states are kept distinct:
// real (backend says connected), demo (backend says simulated/missing), and
// unknown (request failed or fields absent) - unknown is NEVER treated as
// real, so the UI can never claim a live checkout it cannot prove.
import { useEffect, useState } from "react";

const ROOT = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");

const UNKNOWN = { unknown: true, payments_simulated: true, video_missing: true, email_missing: true, google_missing: true };

export function mapCapabilities(d) {
  const c = (d && d.capabilities) || {};
  // Absent fields are treated as not connected, never as real.
  return {
    unknown: false,
    payments_simulated: c.payments ? c.payments === "mock" : true,
    video_missing: c.ai_video ? c.ai_video === "none" : true,
    email_missing: c.email ? c.email === "not_configured" : true,
    google_missing: c.google_auth ? c.google_auth === "unavailable" : true,
  };
}

let cached = null;
export function fetchDemo() {
  if (!cached) {
    cached = fetch(`${ROOT}/api`)
      .then((r) => {
        if (!r.ok) throw new Error("capability check failed");
        return r.json();
      })
      .then(mapCapabilities)
      .catch(() => UNKNOWN);
  }
  return cached;
}

export function useDemo() {
  // Until the fetch lands, everything is unknown - and unknown renders as demo.
  const [flags, setFlags] = useState(UNKNOWN);
  useEffect(() => {
    let live = true;
    fetchDemo().then((f) => live && setFlags(f));
    return () => { live = false; };
  }, []);
  flags.demo = flags.unknown || flags.payments_simulated || flags.video_missing || flags.email_missing || flags.google_missing;
  return flags;
}
