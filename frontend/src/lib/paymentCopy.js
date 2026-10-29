// Added in the local rebuild (not part of the recovered original code).
// Payment-page copy derived from THIS order's stored provider (order-specific
// evidence from /api/payments/status), never from global config alone.
// Only an explicit "mock" provider justifies "no payment was taken"; only an
// explicit live provider justifies "payment received"; anything else is
// honestly unverified. Email claims follow the same tri-state rule: promise
// email only when email is explicitly "real", state it is missing only when
// explicitly "demo", and say it is unverified when "unknown".

const LIVE_PROVIDERS = ["stripe"];

export function paymentCopy({ provider, email }) {
  if (provider === "mock") {
    return {
      variant: "demo",
      eyebrow: "Demo order recorded ✓",
      title: "Your demo order is in.",
      body: (ref) =>
        `Order #${ref} was recorded in this local build. No payment was taken.` +
        (email === "demo" ? " No emails will be sent." : ""),
    };
  }
  if (LIVE_PROVIDERS.includes(provider)) {
    return {
      variant: "paid",
      eyebrow: "Payment received ✓",
      title: "You're in.",
      body: (ref) =>
        `Order #${ref}.` +
        (email === "real"
          ? " We'll email you a script to approve."
          : email === "demo"
            ? " Email is not connected in this build, so no confirmation email will arrive."
            : " Email delivery could not be verified in this build."),
    };
  }
  return {
    variant: "unverified",
    eyebrow: "Payment status unverified",
    title: "We couldn't verify this payment.",
    body: (ref) =>
      `Order #${ref} is recorded, but this build cannot verify whether any payment was taken.`,
  };
}
