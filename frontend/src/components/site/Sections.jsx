import { useClosed } from "@/lib/demo";

const STEPS = [
  {
    title: "Send a photo + script idea",
    svg: (
      <svg viewBox="0 0 200 140" className="w-full h-auto mb-4" aria-hidden="true">
        <rect x="70" y="6" width="60" height="128" rx="10" fill="#111" /><rect x="76" y="16" width="48" height="96" rx="4" fill="#ffd2c2" />
        <circle cx="100" cy="52" r="14" fill="#111" /><path d="M82 112 Q100 74 118 112 Z" fill="#111" />
        <circle cx="100" cy="123" r="5" fill="#ff5a2e" /><path d="M20 70 h36 M44 58 l12 12 -12 12" fill="none" stroke="#111" strokeWidth="3" />
      </svg>
    ),
  },
  {
    title: "We build your avatar",
    svg: (
      <svg viewBox="0 0 200 140" className="w-full h-auto mb-4" aria-hidden="true">
        <rect x="20" y="14" width="160" height="96" fill="#111" /><rect x="28" y="22" width="90" height="80" fill="#ffd2c2" />
        <circle cx="73" cy="52" r="14" fill="#111" /><path d="M53 102 Q73 66 93 102 Z" fill="#111" />
        <rect x="126" y="26" width="46" height="8" fill="#ff5a2e" /><rect x="126" y="42" width="46" height="6" fill="#f7f5ef" />
        <rect x="126" y="54" width="32" height="6" fill="#f7f5ef" /><rect x="10" y="110" width="180" height="10" fill="#111" />
      </svg>
    ),
  },
  {
    title: "Your video, ready to post",
    svg: (
      <svg viewBox="0 0 200 140" className="w-full h-auto mb-4" aria-hidden="true">
        <rect x="40" y="10" width="120" height="120" fill="#111" /><polygon points="88,48 122,70 88,92" fill="#ff5a2e" />
        <circle cx="60" cy="118" r="4" fill="#f7f5ef" /><path d="M140 22 l8 8 14-16" fill="none" stroke="#ff5a2e" strokeWidth="4" />
      </svg>
    ),
  },
];

export const HowItWorks = () => {
  const closed = useClosed();
  return (
  <section id="how" className="bg-signal text-ink py-24 md:py-32" data-testid="how-section">
    <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
      <p className="lab">How it works</p>
      <div className="min-w-0">
        <h2 className="dsp h2-xl mb-12">{closed ? "How it will work." : "Brief Monday. Post Friday."}</h2>
        <ol className="grid md:grid-cols-3 gap-6">
          {STEPS.map((s, i) => (
            <li key={s.title} className="card-pop bg-ground border-2 border-ink p-4" data-testid={`how-step-${i + 1}`}>
              <span className="lab">Step {i + 1}</span>
              {s.svg}
              <p className="dsp text-2xl mt-2">{s.title}</p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  </section>
);
};

const ROWS = [
  ["Cost", "Crew, studio, edit", "Much cheaper · £350"],
  ["Turnaround", "Weeks", "Ready in days, not weeks"],
  ["On camera", "You, under lights", "No camera, no studio, you never appear"],
  ["Languages", "One", "Looks like you, speaks many languages"],
];

const ROWS_CLOSED = ROWS.map(([k, a, b]) =>
  k === "Turnaround" ? [k, a, "To be published when ordering opens"]
  : k === "Languages" ? [k, a, "Looks like you; other languages planned"]
  : [k, a, b]);

export const WhyTable = () => {
  const rows = useClosed() ? ROWS_CLOSED : ROWS;
  return (
  <section id="why" className="bg-ground py-24 md:py-32" data-testid="why-section">
    <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
      <p className="lab">Why DoppelAI</p>
      <div className="min-w-0">
        <h2 className="dsp h2-xl mb-12">Skip the shoot, not the quality</h2>
        <div className="border-2 border-ink overflow-x-auto">
          <table className="w-full text-left text-sm md:text-base">
            <thead className="bg-ink text-ground">
              <tr><th className="p-2 md:p-4 lab" /><th className="p-2 md:p-4 lab">Film crew</th><th className="p-2 md:p-4 lab text-signal">DoppelAI</th></tr>
            </thead>
            <tbody className="divide-y-2 divide-ink">
              {rows.map(([k, a, b]) => (
                <tr key={k} className="hover:bg-blush/50 transition-colors">
                  <td className="p-2 md:p-4 dsp text-base md:text-xl">{k}</td><td className="p-2 md:p-4">{a}</td><td className="p-2 md:p-4 font-semibold tab">{b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
);
};

const WHO = ["Local businesses", "Startups & online brands", "Agencies who resell", "Coaches & personal brands"];

export const WhoFor = () => (
  <section id="who" className="bg-ink text-ground py-24 md:py-32" data-testid="who-section">
    <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
      <p className="lab text-signal">Made for</p>
      <ul className="min-w-0 dsp text-[clamp(32px,4vw,56px)] leading-[1.05] divide-y-2 divide-ground/30">
        {WHO.map((w) => (
          <li key={w} className="py-3 flex justify-between gap-4 hover:text-signal transition-colors">
            {w}<span className="text-signal">✦</span>
          </li>
        ))}
      </ul>
    </div>
  </section>
);
