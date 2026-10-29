import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Shell } from "@/components/site/Shell";
import { useAuth } from "@/context/AuthContext";
import { useOrder } from "@/context/OrderContext";
import { api } from "@/lib/api";

const Card = ({ children, testId }) => (
  <section className="max-w-2xl mx-auto px-6 py-24">
    <div className="border-2 border-ink bg-white shadow-signal-xl p-8 md:p-12" data-testid={testId}>{children}</div>
  </section>
);

export function PaymentSuccess() {
  const [params] = useSearchParams();
  const { user } = useAuth();
  const [state, setState] = useState({ status: "checking" });

  useEffect(() => {
    const sessionId = params.get("session_id");
    let attempts = 0;
    let timer;
    const poll = async () => {
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        if (data.payment_status === "paid") return setState({ status: "paid", ref: data.order_ref });
        if (data.status === "expired") return setState({ status: "expired" });
      } catch {
        return setState({ status: "error" });
      }
      attempts += 1;
      if (attempts >= 15) return setState({ status: "pending" });
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => clearTimeout(timer);
  }, [params]);

  return (
    <Shell testId="payment-success-page">
      <Card testId="payment-status-card">
        {state.status === "checking" && <p className="dsp text-3xl animate-pulse" data-testid="payment-checking">Confirming your payment…</p>}
        {state.status === "paid" && (
          <>
            <p className="lab text-signal mb-3">Payment received ✓</p>
            <h1 className="dsp h2-xl" data-testid="payment-success-title">You're in. Your double is on the way.</h1>
            <p className="mt-4">Order <strong className="tab" data-testid="payment-order-ref">#{state.ref}</strong>. We'll email you a script to approve, then your video lands in days.</p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link to={user ? "/dashboard" : "/login?next=/dashboard"} className="dsp text-xl bg-signal border-2 border-ink px-6 py-3 shadow-hard-md" data-testid="payment-go-dashboard">
                {user ? "Go to my studio" : "Create account to track it"}
              </Link>
              <Link to="/" className="lab underline self-center" data-testid="payment-back-home">Back to site</Link>
            </div>
          </>
        )}
        {["pending", "error", "expired"].includes(state.status) && (
          <>
            <h1 className="dsp h2-xl" data-testid="payment-pending-title">
              {state.status === "expired" ? "That checkout expired." : "We couldn't confirm it yet."}
            </h1>
            <p className="mt-4">If you were charged, your order is safe. Refresh in a minute, or start again below.</p>
            <Link to="/#pricing" className="inline-block mt-8 dsp text-xl bg-signal border-2 border-ink px-6 py-3" data-testid="payment-retry-link">Back to pricing</Link>
          </>
        )}
      </Card>
    </Shell>
  );
}

export function PaymentCancel() {
  const { openOrder } = useOrder();
  return (
    <Shell testId="payment-cancel-page">
      <Card testId="payment-cancel-card">
        <h1 className="dsp h2-xl">No worries. Nothing was charged.</h1>
        <p className="mt-4">Still thinking? Try a free script or teaser first, or pick up where you left off.</p>
        <div className="mt-8 flex flex-wrap gap-4">
          <button type="button" onClick={() => openOrder()} className="dsp text-xl bg-signal border-2 border-ink px-6 py-3 shadow-hard-md" data-testid="cancel-retry-button">Try checkout again</button>
          <Link to="/#try" className="lab underline self-center" data-testid="cancel-try-free-link">Try it free first</Link>
        </div>
      </Card>
    </Shell>
  );
}
