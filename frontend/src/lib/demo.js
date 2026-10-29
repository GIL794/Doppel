// Added in the local rebuild (not part of the recovered original code).
// Asks the backend once whether it is running in demo mode (mock payments /
// no AI provider) and lets the UI label itself honestly when it is.
import { useEffect, useState } from "react";

const ROOT = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");

let cached = null;
export function fetchDemo() {
  if (!cached) {
    cached = fetch(`${ROOT}/api`)
      .then((r) => (r.ok ? r.json() : {}))
      .then((d) => d.demo === true)
      .catch(() => false);
  }
  return cached;
}

export function useDemo() {
  const [demo, setDemo] = useState(false);
  useEffect(() => {
    let live = true;
    fetchDemo().then((d) => live && setDemo(d));
    return () => { live = false; };
  }, []);
  return demo;
}
