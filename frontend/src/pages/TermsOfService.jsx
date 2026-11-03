import { Shell } from "@/components/site/Shell";

export default function TermsOfService() {
  return (
    <Shell testId="terms-of-service-page">
      <div className="bg-ground py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-6">
          <div className="border-2 border-ink bg-white p-8 md:p-12 shadow-signal-lg space-y-8">
            <div>
              <p className="lab text-signal mb-2">Legal & Compliance</p>
              <h1 className="dsp text-4xl md:text-5xl">Terms of Service</h1>
              <p className="lab text-graphite mt-2">Effective Date: November 2, 2026 · Governing Law: England &amp; Wales</p>
            </div>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">1. Agreement to Terms</h2>
              <p className="text-base leading-relaxed">
                These Terms of Service (&quot;Terms&quot;) constitute a legally binding agreement between you (&quot;Client&quot;, &quot;you&quot;) and DoppelAI Ltd (&quot;DoppelAI&quot;, &quot;we&quot;, &quot;us&quot;), governing your purchase and use of our AI avatar promo video services, teaser studio, and web platform.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">2. The Commercial Package (£350 Fixed Fee)</h2>
              <p className="text-base leading-relaxed">
                Our standard commercial video package costs £350 (inclusive of applicable taxes where stated) and includes:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-base">
                <li>One customized video up to 60 seconds in duration.</li>
                <li>One custom spokesperson avatar based either on your uploaded clear portrait photo or a selected synthetic face.</li>
                <li>Delivery in three formats: Vertical (9:16), Square (1:1), and Wide (16:9).</li>
                <li>Spoken dialogue in your selected language.</li>
                <li><strong>The Human Approval Gate:</strong> A drafted script provided for your explicit approval before any video rendering begins.</li>
                <li>One full round of script revisions prior to rendering.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">3. Likeness Rights, Authority &amp; Warranties</h2>
              <p className="text-base leading-relaxed">
                By uploading any photograph, audio recording, brand trademark, or script brief to DoppelAI, you expressly represent and warrant that:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-base">
                <li>You are the individual depicted in the photograph, or you possess verifiable written authority and consent from the depicted individual to generate synthetic video likenesses on their behalf.</li>
                <li>You own or have secured all necessary intellectual property licenses for all logos, trademarks, and brand assets submitted.</li>
                <li>The media submitted does not depict any minor under 18 years of age.</li>
                <li>The media submitted does not depict any celebrity, public figure, or politician without prior written licensing agreement.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">4. Acceptable Use Policy</h2>
              <p className="text-base leading-relaxed">
                You agree not to use DoppelAI to generate, promote, or distribute any material that is:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-base">
                <li>Defamatory, libelous, harassing, bullying, or abusive.</li>
                <li>Fraudulent, misleading, deceptive, or impersonating a regulated profession (e.g. medical, legal, or financial advice).</li>
                <li>Sexually explicit, pornographic, violent, or encouraging self-harm.</li>
                <li>Violative of any copyright, trademark, privacy, or publicity right.</li>
              </ul>
              <p className="text-base leading-relaxed">
                We reserve the absolute right to cancel any order and terminate any account that violates this policy without prior notice.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">5. Intellectual Property &amp; Commercial Licensing</h2>
              <p className="text-base leading-relaxed">
                <strong>Your Content:</strong> You retain full ownership of your submitted briefs, trademarks, logos, and raw portrait photos.<br />
                <strong>Delivered Video:</strong> Upon full payment of the £350 package, DoppelAI grants you a worldwide, perpetual, royalty-free, transferable license to distribute, broadcast, and display the final delivered video for your commercial and marketing purposes.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">6. Cancellation, Revisions &amp; Refunds</h2>
              <p className="text-base leading-relaxed">
                Pursuant to the Consumer Contracts Regulations 2013 and the Consumer Rights Act 2015:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-base">
                <li><strong>Prior to Script Approval:</strong> You may cancel your order at any time before clicking &quot;Approve Script&quot; and receive a 100% full refund.</li>
                <li><strong>Bespoke Custom Media:</strong> Because video rendering produces a highly bespoke, personalized digital product created to your exact specifications, once you have approved the script and video rendering begins, the £350 fee is non-refundable, except in the event of an unresolvable technical defect.</li>
                <li><strong>Quality Guarantee:</strong> In the event of a verified technical defect (e.g. distorted audio, severe lip-sync failure), we will re-render your video at zero cost.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">7. Limitation of Liability &amp; Jurisdiction</h2>
              <p className="text-base leading-relaxed">
                To the maximum extent permitted by applicable law, DoppelAI Ltd shall not be liable for any indirect, incidental, or consequential damages resulting from your use or public distribution of synthetic media generated by our service. These Terms are governed exclusively by the laws of England and Wales, with exclusive jurisdiction in the Courts of London.
              </p>
            </section>
          </div>
        </div>
      </div>
    </Shell>
  );
}

