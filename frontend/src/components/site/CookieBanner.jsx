import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export const CookieBanner = () => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const acknowledged = localStorage.getItem("doppel_cookie_ack");
    if (!acknowledged) {
      setVisible(true);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem("doppel_cookie_ack", "true");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <aside
      aria-label="Cookie and Privacy Notice"
      className="fixed bottom-0 inset-x-0 z-50 bg-ink text-ground border-t-2 border-signal p-4 md:p-6 shadow-2xl transition-transform"
      data-testid="cookie-banner"
    >
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <p className="lab text-signal">Privacy &amp; Essential Cookies</p>
          <p className="text-sm md:text-base text-ground/90 max-w-3xl">
            We use strictly necessary cookies to keep you signed in and process your video orders securely. We never deploy third-party advertising or cross-site tracking cookies. By continuing to use our service, you agree to our{" "}
            <Link to="/privacy" className="underline hover:text-signal transition-colors font-medium">Privacy Policy</Link> and{" "}
            <Link to="/cookies" className="underline hover:text-signal transition-colors font-medium">Cookie Policy</Link>.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            to="/cookies"
            className="lab border border-ground/40 px-3 py-2 text-xs hover:border-signal hover:text-signal transition-colors"
          >
            Learn more
          </Link>
          <button
            type="button"
            onClick={dismiss}
            className="bg-signal text-ink lab px-5 py-2 text-xs md:text-sm font-semibold hover:bg-white transition-colors"
            data-testid="cookie-banner-accept"
          >
            Got it
          </button>
        </div>
      </div>
    </aside>
  );
};

