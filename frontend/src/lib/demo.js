// Added in the local rebuild (not part of the recovered original code).
// Asks the backend once which capabilities are real versus simulated.
// Every capability is tri-state: "real" (explicitly connected), "demo"
// (explicitly simulated/absent) or "unknown" (fetch failed or the value is
// not recognised). Unknown is NEVER treated as real, and also never as proof
// of absence - only explicit demo values justify "not connected" claims.
import { useEffect, useState } from "react";

const ROOT = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");

// Explicit allowlists: anything not listed here stays "unknown".
const KNOWN = {
  payments: { mock: "demo", stripe: "real", closed: "closed" },
  ai_video: { none: "demo", configured: "real" },
  ai_script: { template: "demo", configured: "real" },
  email: { not_configured: "demo", configured: "real" },
  google_auth: { not_configured: "demo", configured: "real" },
};

const ALL_UNKNOWN = { unknown: true, payments: "unknown", ai_video: "unknown", ai_script: "unknown", email: "unknown", google_auth: "unknown" };

export function mapCapabilities(d) {
  const c = (d && d.capabilities) || {};
  const map = {};
  for (const key of Object.keys(KNOWN)) {
    map[key] = KNOWN[key][c[key]] || "unknown";
  }
  return { unknown: false, ...map };
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
      .catch(() => ALL_UNKNOWN);
  }
  return cached;
}

export function useDemo() {
  // Until the fetch lands, everything is unknown - and unknown renders
  // conservatively (demo wording / disabled checkout), never as real.
  const [flags, setFlags] = useState(ALL_UNKNOWN);
  useEffect(() => {
    let live = true;
    fetchDemo().then((f) => live && setFlags(f));
    return () => { live = false; };
  }, []);
  flags.demo =
    flags.unknown ||
    [flags.payments, flags.ai_video, flags.ai_script, flags.email, flags.google_auth].some((s) => s !== "real");
  return flags;
}


// Closed-ordering mode (production build before payments are connected): the
// site must not promise checkout, delivery times or language support.
export function useClosed() {
  return useDemo().payments === "closed";
}
