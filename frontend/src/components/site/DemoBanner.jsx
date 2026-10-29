// Added in the local rebuild (not part of the recovered original code).
// Persistent honesty notice naming exactly which capabilities are not real.
import { useDemo } from "@/lib/demo";

export const DemoBanner = () => {
  const flags = useDemo();
  if (!flags.demo) return null;
  const parts = flags.unknown
    ? ["live capability status unavailable - assume payments, AI video and email are not connected"]
    : [];
  if (flags.payments_simulated) parts.push("payments simulated");
  if (flags.video_missing) parts.push("AI video not connected");
  if (flags.email_missing) parts.push("email not connected");
  if (flags.google_missing) parts.push("Google sign-in unavailable");
  return (
    <div
      className="fixed bottom-0 inset-x-0 z-[100] bg-ink text-ground border-t-2 border-signal px-4 py-2 text-center lab"
      data-testid="demo-banner"
    >
      Local demo: {parts.join(" · ")}
    </div>
  );
};
