import { useClosed } from "@/lib/demo";

export const Samples = () => {
  const closed = useClosed();
  return (
  <section id="samples" className="bg-ground py-24 md:py-32" data-testid="samples-section">
    <div className="max-w-6xl mx-auto px-6">
      <div className="flex flex-wrap items-end justify-between gap-6 mb-12">
        <div className="min-w-0">
          <p className="lab mb-4">What you get</p>
          <h2 className="dsp h2-xl">One video. Every screen.</h2>
        </div>
        <p className="max-w-sm">Each order ships in the formats your channels need.</p>
      </div>
      <div className="st grid md:grid-cols-[1.6fr_1fr] gap-6">
        <div className="card-pop border-2 border-ink bg-ink p-3">
          <div className="flex gap-2 mb-3">
            <span className="w-3 h-3 rounded-full bg-signal" /><span className="w-3 h-3 rounded-full bg-ground" /><span className="w-3 h-3 rounded-full bg-graphite" />
          </div>
          <svg viewBox="0 0 320 180" className="w-full h-auto block" aria-hidden="true">
            <rect width="320" height="180" fill="#f7f5ef" /><rect x="180" y="0" width="140" height="180" fill="#ffd2c2" />
            <circle cx="250" cy="70" r="28" fill="#111" /><path d="M200 180 Q250 100 300 180 Z" fill="#111" />
            <text x="20" y="60" fontFamily="Impact,sans-serif" fontSize="26" fill="#111">SPRING OFFER</text>
            <rect x="20" y="74" width="120" height="6" fill="#111" /><rect x="20" y="88" width="90" height="6" fill="#111" opacity=".4" />
            <rect x="20" y="112" width="70" height="22" fill="#ff5a2e" />
            <rect x="0" y="166" width="320" height="4" fill="#111" opacity=".2" /><rect x="0" y="166" width="130" height="4" fill="#ff5a2e" />
          </svg>
          <p className="lab text-ground mt-3">16:9 · Website &amp; YouTube</p>
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div className="card-pop border-2 border-ink bg-blush p-3 flex flex-col">
            <svg viewBox="0 0 90 160" className="w-full h-auto" aria-hidden="true">
              <rect width="90" height="160" rx="8" fill="#111" /><circle cx="45" cy="60" r="16" fill="#ff5a2e" />
              <path d="M20 130 Q45 80 70 130 Z" fill="#ff5a2e" /><rect x="10" y="138" width="70" height="10" rx="3" fill="#f7f5ef" />
            </svg>
            <p className="lab mt-3">9:16 · Reels &amp; TikTok</p>
          </div>
          <div className="card-pop border-2 border-ink bg-ground p-3 flex flex-col">
            <svg viewBox="0 0 90 90" className="w-full h-auto" aria-hidden="true">
              <rect width="90" height="90" fill="#111" /><circle cx="45" cy="38" r="14" fill="#f7f5ef" />
              <path d="M22 90 Q45 50 68 90 Z" fill="#f7f5ef" /><rect x="8" y="8" width="26" height="10" fill="#ff5a2e" />
            </svg>
            <p className="lab mt-3">1:1 · Feed posts</p>
          </div>
          <div className="col-span-2 card-pop border-2 border-ink bg-ink text-ground p-4">
            <p className="lab mb-3">{closed ? "Voice sample" : "Voice in any language"}</p>
            <svg viewBox="0 0 200 30" className="w-full h-6" aria-hidden="true">
              <g fill="#ff5a2e">
                {[[0,12,6],[12,6,18],[24,2,26],[36,9,12],[48,4,22],[60,11,8],[72,5,20],[84,0,30],[96,8,14],[108,3,24],[120,10,10],[132,6,18],[144,12,6],[156,4,22],[168,9,12],[180,12,6]].map(([x, y, h]) => (
                  <rect key={x} x={x} y={y} width="6" height={h} />
                ))}
              </g>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </section>
);
};
