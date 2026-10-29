import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useOrder } from "@/context/OrderContext";

const INCLUDED = [
  "Up to 60 seconds, your script polished",
  "Custom avatar, your look or a new face",
  "One language of your choice",
  "Vertical, square and wide cuts",
  "One round of revisions",
];

export const Pricing = () => {
  const { openOrder } = useOrder();
  return (
    <section id="pricing" className="bg-ground py-24 md:py-32" data-testid="pricing-section">
      <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
        <p className="lab">The package</p>
        <div className="min-w-0 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <p className="dsp big tab" data-testid="pricing-amount">£350</p>
            <p className="dsp text-2xl mt-2">One promo video. Fixed price.</p>
            <p className="mt-4 max-w-sm">No hidden extras. You approve the script before we render.</p>
          </div>
          <div className="border-2 border-ink bg-white shadow-signal-lg p-6" data-testid="pricing-card">
            <div className="flex justify-between lab mb-4"><span>Checkout</span><span>Encrypted · Stripe</span></div>
            <ul className="space-y-3 mb-6">
              {INCLUDED.map((i) => <li key={i}>✓ {i}</li>)}
            </ul>
            <div className="flex justify-between border-t-2 border-ink pt-4 mb-4 dsp text-2xl tab"><span>Total</span><span>£350</span></div>
            <button type="button" onClick={() => openOrder()}
              className="group w-full bg-signal text-ink dsp text-2xl px-6 py-5 border-2 border-ink hover:bg-ink hover:text-ground transition-colors"
              data-testid="pricing-pay-button">
              Pay £350 &amp; start <span className="inline-block transition-transform group-hover:translate-x-1">→</span>
            </button>
            <div className="flex flex-wrap gap-2 mt-4 lab">
              {["Visa", "Mastercard", "Apple Pay"].map((m) => <span key={m} className="border border-ink px-2 py-1">{m}</span>)}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export const Reviews = () => (
  <section id="reviews" className="bg-ground pb-24 md:pb-32" data-testid="reviews-section">
    <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
      <p className="lab">Reviews</p>
      <div className="min-w-0 border-2 border-dashed border-ink p-12">
        <p className="dsp big text-quote">“ ”</p>
        <p className="dsp text-2xl">Words from our first clients will land here.</p>
      </div>
    </div>
  </section>
);

const FAQS = [
  ["Do I have to film anything?", "No. One clear photo is enough to build your avatar."],
  ["How fast is it?", "Days, not weeks. Usually about five working days."],
  ["Can it speak Spanish?", "Yes, your avatar can speak many languages."],
  ["Can agencies resell it?", "Yes. Order for each client and deliver under your brand."],
  ["Does the avatar have to look like me?", "No. Choose your own look, or pick a brand-new face to present for you."],
  ["Can I try before I pay?", "Yes. Write a free script above, and make up to two free talking teasers with an account."],
];

export const Faq = () => (
  <section id="faq" className="bg-ground pb-24 md:pb-32" data-testid="faq-section">
    <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
      <p className="lab">FAQ</p>
      <Accordion type="single" collapsible className="min-w-0 border-y-2 border-ink">
        {FAQS.map(([q, a], i) => (
          <AccordionItem key={q} value={`q${i}`} className="border-b-2 border-ink last:border-b-0">
            <AccordionTrigger className="dsp text-2xl text-left hover:no-underline hover:text-signal" data-testid={`faq-q-${i}`}>{q}</AccordionTrigger>
            <AccordionContent className="text-base">{a}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  </section>
);

export const FinalCta = () => {
  const { openOrder } = useOrder();
  return (
    <section className="bg-signal text-ink py-24 md:py-32" data-testid="final-cta-section">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <h2 className="dsp h2-xl">Stay off camera. Get seen.</h2>
        <button type="button" onClick={() => openOrder()}
          className="inline-block mt-8 bg-ink text-ground dsp text-2xl px-8 py-4 shadow-ground-md hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-[transform,box-shadow]"
          data-testid="final-cta-buy-button">Get my video · £350</button>
        <p className="lab mt-4">Fixed price · Secure checkout</p>
      </div>
    </section>
  );
};

export const Footer = () => (
  <footer className="bg-ink text-ground py-12" data-testid="site-footer">
    <div className="max-w-6xl mx-auto px-6 flex flex-wrap justify-between gap-4 lab">
      <span>Doppel · AI avatar promo videos</span>
      <span className="flex gap-6"><a href="/#how">How</a><a href="/#pricing">Pricing</a><a href="/#faq">FAQ</a></span>
      <span>Online, everywhere</span>
    </div>
  </footer>
);
