import { mapCapabilities } from "./demo";

describe("mapCapabilities", () => {
  it("flags every missing capability in the default local build", () => {
    const f = mapCapabilities({
      capabilities: { payments: "mock", ai_video: "none", email: "not_configured", google_auth: "unavailable" },
    });
    expect(f).toEqual({
      unknown: false,
      payments_simulated: true,
      video_missing: true,
      email_missing: true,
      google_missing: true,
    });
  });

  it("mixed state: real payments do not clear the other demo labels", () => {
    const f = mapCapabilities({
      capabilities: { payments: "stripe", ai_video: "none", email: "not_configured", google_auth: "unavailable" },
    });
    expect(f.payments_simulated).toBe(false);
    expect(f.video_missing).toBe(true);
    expect(f.email_missing).toBe(true);
    expect(f.google_missing).toBe(true);
  });

  it("fully connected backend clears every label", () => {
    const f = mapCapabilities({
      capabilities: { payments: "stripe", ai_video: "configured", email: "configured", google_auth: "available" },
    });
    expect(f.payments_simulated).toBe(false);
    expect(f.video_missing).toBe(false);
    expect(f.email_missing).toBe(false);
    expect(f.google_missing).toBe(false);
  });

  it("absent capability fields are treated as not connected, never as real", () => {
    const f = mapCapabilities({});
    expect(f.payments_simulated).toBe(true);
    expect(f.video_missing).toBe(true);
    expect(f.email_missing).toBe(true);
    expect(f.google_missing).toBe(true);
  });

  it("garbage payload cannot produce a real-looking state", () => {
    const f = mapCapabilities(null);
    expect(f.unknown).toBe(false);
    expect(f.payments_simulated).toBe(true);
  });
});
