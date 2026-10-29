import { paymentCopy } from "./paymentCopy";

describe("paymentCopy", () => {
  it("mock provider claims demo, and 'no emails' only when email is explicitly demo", () => {
    const a = paymentCopy({ provider: "mock", email: "demo" });
    expect(a.variant).toBe("demo");
    expect(a.body(1)).toContain("No payment was taken");
    expect(a.body(1)).toContain("No emails will be sent");
    const b = paymentCopy({ provider: "mock", email: "real" });
    expect(b.body(1)).toContain("No payment was taken");
    expect(b.body(1)).not.toContain("No emails will be sent");
    // unknown email: no email claim in either direction
    const c = paymentCopy({ provider: "mock", email: "unknown" });
    expect(c.body(1)).toContain("No payment was taken");
    expect(c.body(1)).not.toContain("email");
  });

  it("live provider promises email only when email is real", () => {
    const a = paymentCopy({ provider: "stripe", email: "real" });
    expect(a.variant).toBe("paid");
    expect(a.title).not.toMatch(/double|video/i);
    expect(a.body(1)).toContain("We'll email you");
    expect(a.body(1)).not.toMatch(/video/i);
  });

  it("live provider with email demo states email is missing, does not promise it", () => {
    const b = paymentCopy({ provider: "stripe", email: "demo" });
    expect(b.body(1)).toContain("no confirmation email will arrive");
    expect(b.body(1)).not.toContain("We'll email you a script");
  });

  it("live provider with email unknown claims neither promise nor absence", () => {
    const c = paymentCopy({ provider: "stripe", email: "unknown" });
    expect(c.variant).toBe("paid");
    expect(c.body(1)).toContain("could not be verified");
    expect(c.body(1)).not.toContain("We'll email you a script");
    expect(c.body(1)).not.toContain("no confirmation email will arrive");
  });

  it("null provider claims nothing in either direction", () => {
    const c = paymentCopy({ provider: null, email: "demo" });
    expect(c.variant).toBe("unverified");
    expect(c.body(1)).not.toContain("No payment was taken");
    expect(c.body(1)).not.toContain("Payment received");
    expect(c.body(1)).not.toMatch(/email/i);
  });

  it("unexpected nonempty provider stays unverified, never real", () => {
    const c = paymentCopy({ provider: "paypal", email: "real" });
    expect(c.variant).toBe("unverified");
    expect(c.body(1)).not.toContain("We'll email you");
  });
});
