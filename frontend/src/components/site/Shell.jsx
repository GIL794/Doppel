import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Closing";

export const Shell = ({ children, testId }) => (
  <div className="min-h-screen flex flex-col overflow-x-hidden" data-testid={testId}>
    <Header />
    <main className="flex-1">{children}</main>
    <Footer />
  </div>
);

export const Loading = () => (
  <div className="min-h-[60vh] flex items-center justify-center" data-testid="loading-state">
    <span className="lab animate-pulse">Loading…</span>
  </div>
);

export const fieldCls = "rounded-none border-2 border-ink bg-white h-12 text-base focus-visible:ring-signal";

export const PrimaryBtn = ({ children, className = "", ...props }) => (
  <button
    {...props}
    className={`w-full bg-signal text-ink dsp text-xl px-6 py-4 border-2 border-ink shadow-hard-md hover:shadow-hard-hover hover:translate-x-1 hover:translate-y-1 transition-[transform,box-shadow] disabled:opacity-60 disabled:pointer-events-none ${className}`}
  >
    {children}
  </button>
);
