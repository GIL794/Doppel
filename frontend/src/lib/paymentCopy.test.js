import { paymentCopy } from "./paymentCopy";

describe("paymentCopy", () => {
  it("explicit mock: no-payment claim, email claim only when email explicitly missing", () => {
    const a = paymentCopy({ provider: "mock", emailMissing: true });
    expect(a.variant).toBe("demo");
    expect(a.eyebrow).toMatch(/Demo order recorded/);
    expect(a.body(7)).toBe("Order #7 was recorded in this local build. No payment was taken. No emails will be sent.");
    const b = paymentCopy({ provider: "mock", emailMissing: false });
    expect(b.body(7)).not.toMatch(/No emails/);
  });

  it("live provider: received claim; email promise only when email connected", () => {
    const a = paymentCopy({ provider: "stripe", emailMissing: false });
    expect(a.variant).toBe("paid");
    expect(a.body(7)).toBe("Order #7. We'll email you a script to approve.");
    const b = paymentCopy({ provider: "stripe", emailMissing: true });
    expect(b.body(7)).toMatch(/no confirmation email/);
    expect(b.body(7)).not.toMatch(/We'll email/);
    // no video delivery promise in this rebuild
    expect(a.body(7)).not.toMatch(/video lands/);
  });

  it("null provider (pre-migration order): unverified, claims nothing either way", () => {
    const c = paymentCopy({ provider: null, emailMissing: true });
    expect(c.variant).toBe("unverified");
    expect(c.body(7)).not.toMatch(/No payment was taken/);
    expect(c.body(7)).not.toMatch(/Payment received/);
    expect(c.body(7)).toMatch(/cannot verify/);
  });

  it("unexpected provider string: unverified, never received and never no-charge", () => {
    const c = paymentCopy({ provider: "paypal", emailMissing: false });
    expect(c.variant).toBe("unverified");
    expect(c.eyebrow).not.toMatch(/Payment received/);
    expect(c.body(7)).not.toMatch(/No payment was taken/);
  });
});
