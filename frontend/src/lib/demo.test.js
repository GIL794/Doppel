import { mapCapabilities } from "./demo";

describe("mapCapabilities allowlists", () => {
  it("maps the default local build to demo on every capability", () => {
    const f = mapCapabilities({
      capabilities: { payments: "mock", ai_video: "none", ai_script: "template", email: "not_configured", google_auth: "not_configured" },
    });
    expect(f).toEqual({ unknown: false, payments: "demo", ai_video: "demo", ai_script: "demo", email: "demo", google_auth: "demo" });
  });

  it("mixed state: real payments do not clear the other demo labels", () => {
    const f = mapCapabilities({
      capabilities: { payments: "stripe", ai_video: "none", email: "not_configured", google_auth: "not_configured" },
    });
    expect(f.payments).toBe("real");
    expect(f.ai_video).toBe("demo");
    expect(f.email).toBe("demo");
    expect(f.google_auth).toBe("demo");
  });

  it("fully connected backend clears every label", () => {
    const f = mapCapabilities({
      capabilities: { payments: "stripe", ai_video: "configured", ai_script: "configured", email: "configured", google_auth: "configured" },
    });
    expect([f.payments, f.ai_video, f.ai_script, f.email, f.google_auth]).toEqual(["real", "real", "real", "real", "real"]);
  });

  it("unexpected NON-EMPTY values are unknown, never real", () => {
    const f = mapCapabilities({
      capabilities: { payments: "paypal", ai_video: "runway", ai_script: "openai", email: "ses", google_auth: "oauth2" },
    });
    expect([f.payments, f.ai_video, f.ai_script, f.email, f.google_auth]).toEqual(["unknown", "unknown", "unknown", "unknown", "unknown"]);
  });

  it("absent fields are unknown, never real and never asserted absent", () => {
    const f = mapCapabilities({});
    expect([f.payments, f.ai_video, f.ai_script, f.email, f.google_auth]).toEqual(["unknown", "unknown", "unknown", "unknown", "unknown"]);
  });

  it("garbage payload yields all-unknown, not real", () => {
    const f = mapCapabilities(null);
    expect(f.payments).toBe("unknown");
    expect(f.email).toBe("unknown");
  });
});

describe("fetchDemo failure", () => {
  beforeEach(() => jest.resetModules());

  it("fetch rejection resolves to all-unknown (never real)", async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error("network down")));
    const { fetchDemo } = require("./demo");
    const f = await fetchDemo();
    expect(f.unknown).toBe(true);
    expect([f.payments, f.ai_video, f.ai_script, f.email, f.google_auth]).toEqual(["unknown", "unknown", "unknown", "unknown", "unknown"]);
  });

  it("non-200 response resolves to all-unknown", async () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: false, status: 500 }));
    const { fetchDemo } = require("./demo");
    const f = await fetchDemo();
    expect(f.unknown).toBe(true);
  });
});


describe("closed ordering", () => {
  it("production backend with no payment provider reports closed, not real or demo", () => {
    expect(mapCapabilities({ capabilities: { payments: "closed" } }).payments).toBe("closed");
  });
});
