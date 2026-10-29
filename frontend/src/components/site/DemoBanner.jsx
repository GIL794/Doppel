// Added in the local rebuild (not part of the recovered original code).
// Persistent honesty notice naming exactly what is simulated - and, when a
// capability's state cannot be verified, saying "not verified" rather than
// asserting it is absent.
import { useDemo } from "@/lib/demo";

const LABELS = {
  payments: ["payments simulated", "payments not verified"],
  ai_video: ["AI video not connected", "AI video not verified"],
  email: ["email not connected", "email not verified"],
  google_auth: ["Google sign-in unavailable", "Google sign-in not verified"],
};

export const DemoBanner = () => {
  const flags = useDemo();
  if (!flags.demo) return null;
  const parts = Object.entries(LABELS)
    .filter(([key]) => flags[key] !== "real")
    .map(([key, [demo, unknown]]) => (flags[key] === "unknown" ? unknown : demo));
  return (
    <div
      className="fixed bottom-0 inset-x-0 z-[100] bg-ink text-ground border-t-2 border-signal px-4 py-2 text-center lab"
      data-testid="demo-banner"
    >
      Local demo: {parts.join(" · ")}
    </div>
  );
};
