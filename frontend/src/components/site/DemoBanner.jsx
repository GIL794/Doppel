// Added in the local rebuild (not part of the recovered original code).
// Persistent honesty notice shown whenever the backend reports demo mode.
import { useDemo } from "@/lib/demo";

export const DemoBanner = () => {
  const demo = useDemo();
  if (!demo) return null;
  return (
    <div
      className="fixed bottom-0 inset-x-0 z-[100] bg-ink text-ground border-t-2 border-signal px-4 py-2 text-center lab"
      data-testid="demo-banner"
    >
      DEMO BUILD · No real payments, no AI video generation, no emails sent - everything here is simulated locally
    </div>
  );
};
