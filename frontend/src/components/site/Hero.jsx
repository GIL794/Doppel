import { useOrder } from "@/context/OrderContext";
import { useClosed } from "@/lib/demo";

const PhoneMock = ({ closed }) => (
  <div className="dp gr min-w-0" data-testid="hero-visual">
    <div className="tilt relative">
      <svg viewBox="0 0 420 420" className="absolute inset-0 w-full h-full" aria-hidden="true">
        <g className="spin-slow">
          <circle cx="210" cy="210" r="200" fill="none" stroke="#111" strokeWidth="2" strokeDasharray="6 10" />
        </g>
      </svg>
      <div className="relative mx-auto w-[62%] aspect-[9/16] bg-ink rounded-[28px] p-2 shadow-signal-xl">
        <div className="relative w-full h-full rounded-[22px] bg-blush overflow-hidden">
          <svg viewBox="0 0 180 320" className="w-full h-full" aria-hidden="true">
            <rect width="180" height="320" fill="#ffd2c2" />
            <circle cx="90" cy="120" r="38" fill="#111" />
            <circle cx="78" cy="116" r="4" fill="#f7f5ef" />
            <circle cx="102" cy="116" r="4" fill="#f7f5ef" />
            <path className="drw" pathLength="1" d="M76 134 Q90 146 104 134" fill="none" stroke="#ff5a2e" strokeWidth="4" strokeLinecap="round" />
            <path d="M30 260 Q90 160 150 260 Z" fill="#111" />
            <rect x="12" y="14" width="44" height="16" rx="8" fill="#ff5a2e" />
            <text x="20" y="26" fontSize="9" fontFamily="Menlo,monospace" fill="#111">● AI</text>
            <rect x="18" y="270" width="144" height="30" rx="6" fill="#f7f5ef" />
            <text x="26" y="289" fontSize="10" fontFamily="Menlo,monospace" fill="#111">Hi! Visit us this week…</text>
          </svg>
        </div>
      </div>
      {!closed && <div className="fl1 absolute left-0 top-[18%] bg-ground border-2 border-ink px-3 py-2 lab shadow-hard-sm">EN · ES · FR · DE</div>}
      <div className="fl2 absolute right-0 bottom-[16%] bg-ink text-ground px-3 py-2 lab">
        <span className="text-signal">▶</span> 0:45 · 9:16
      </div>
    </div>
  </div>
);

export const Hero = () => {
  const { openOrder } = useOrder();
  const closed = useClosed();
  return (
    <section className="bg-ground py-24 md:py-32" id="top" data-testid="hero-section">
      <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[1fr_1.1fr] gap-12 items-center">
        <div className="min-w-0">
          <p className="lab mb-6 fu f1 inline-flex items-center gap-2 border-2 border-ink rounded-full px-3 py-1">
            <span className="w-2 h-2 rounded-full bg-signal" />AI avatar promo videos
          </p>
          <h1 className="dsp h1-xl" data-testid="hero-title">
            <span className="ln"><span>Your face.</span></span>
            <span className="ln"><span>Zero filming.</span></span>
          </h1>
          <p className="mt-6 max-w-md fu f1" data-testid="hero-subtitle">
            An avatar that looks like you sells your business{closed ? "." : ", in any language."}
          </p>
          <div className="mt-8 fu f2 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={() => openOrder()}
              className="group inline-flex items-center gap-3 bg-signal text-ink dsp text-xl px-6 py-4 border-2 border-ink shadow-hard-md hover:shadow-hard-hover hover:translate-x-1 hover:translate-y-1 transition-[transform,box-shadow]"
              data-testid="hero-buy-button"
            >
              {closed ? "Ordering opens soon" : "Get my video · £350"} <span className="transition-transform group-hover:translate-x-1">→</span>
            </button>
            <a href="#try" className="lab underline underline-offset-4" data-testid="hero-try-free-link">Try it free first</a>
          </div>
          <ul className="mt-8 fu f3 flex flex-wrap gap-x-6 gap-y-2 lab text-graphite">
            {closed ? <><li>✓ Early access</li><li>✓ Free script preview</li></> : <><li>✓ Fixed price</li><li>✓ Secure checkout</li><li>✓ Ready in days</li></>}
          </ul>
        </div>
        <PhoneMock closed={closed} />
      </div>
    </section>
  );
};

const WORDS = ["No camera", "No studio", "Ready in days", "Any language"];
const WORDS_CLOSED = ["No camera", "No studio", "Early access", "Ordering opens soon"];

export const Marquee = () => {
  const closed = useClosed();
  const WORDS_NOW = closed ? WORDS_CLOSED : WORDS;
  return (
  <div className="bg-ink text-ground overflow-hidden py-4 border-y-2 border-ink" aria-hidden="true">
    <div className="mq dsp text-3xl gap-10 pr-10">
      {[...WORDS_NOW, ...WORDS_NOW, ...WORDS_NOW, ...WORDS_NOW].map((w, i) => (
        <span key={i} className="flex gap-10">
          <span>{w}</span><span className="text-signal">✦</span>
        </span>
      ))}
    </div>
  </div>
);
};
