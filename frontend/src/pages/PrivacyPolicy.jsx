import { Shell } from "@/components/site/Shell";

export default function PrivacyPolicy() {
  return (
    <Shell testId="privacy-policy-page">
      <div className="bg-ground py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-6">
          <div className="border-2 border-ink bg-white p-8 md:p-12 shadow-signal-lg space-y-8">
            <div>
              <p className="lab text-signal mb-2">Legal & Compliance</p>
              <h1 className="dsp text-4xl md:text-5xl">Privacy Policy</h1>
              <p className="lab text-graphite mt-2">Last updated: November 2, 2026 · UK GDPR & Data Protection Act 2018 Compliant</p>
            </div>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">1. Overview & Data Controller</h2>
              <p className="text-base leading-relaxed">
                DoppelAI (&quot;we&quot;, &quot;our&quot;, &quot;us&quot;) operates the website and digital video generation platform available at this domain. This Privacy Policy sets out how we collect, process, store, and protect personal data, including facial photographs and derived synthetic likenesses, in full accordance with the UK General Data Protection Regulation (UK GDPR) and the Data Protection Act 2018.
              </p>
              <p className="text-base leading-relaxed">
                <strong>Data Controller:</strong> DoppelAI Ltd, 128 City Road, London, EC1V 2NX, United Kingdom.<br />
                <strong>Privacy &amp; Data Protection Officer Contact:</strong> <a href="mailto:privacy@doppelai.com" className="underline font-semibold">privacy@doppelai.com</a>
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">2. Categories of Data Collected</h2>
              <ul className="list-disc pl-6 space-y-2 text-base">
                <li><strong>Identity &amp; Contact Data:</strong> Name, business name, email address, password hash, and authenticated profile identifiers (e.g., Google OAuth).</li>
                <li><strong>Order &amp; Script Data:</strong> Video language preferences, commercial briefs, product offers, target audience descriptions, and customized marketing scripts.</li>
                <li><strong>Photographic &amp; Biometric Likeness Data (Special Category Data):</strong> Uploaded portrait photographs of yourself, brand logos, and synthetic neural face representations derived solely for generating your approved avatar spokesperson video.</li>
                <li><strong>Financial &amp; Transaction Data:</strong> Payment session identifiers, currency, payment status, and order totals. We do not store raw credit/debit card numbers; all transactions are processed via our PCI-DSS Level 1 certified partner, Stripe Inc.</li>
                <li><strong>Technical &amp; Session Data:</strong> IP addresses, browser user agent, login session tokens stored in secure, HttpOnly cookies, and audit logs.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">3. Lawful Bases for Processing</h2>
              <ul className="list-disc pl-6 space-y-2 text-base">
                <li><strong>Performance of a Contract (UK GDPR Art. 6(1)(b)):</strong> Fulfilling your £350 video order, drafting scripts, rendering cuts, providing customer support, and delivering video files.</li>
                <li><strong>Explicit Consent (UK GDPR Art. 6(1)(a) &amp; Art. 9(2)(a)):</strong> Processing uploaded portrait photos and synthesizing digital facial avatars requires your affirmative, recorded consent upon checkout or teaser generation.</li>
                <li><strong>Legitimate Interests (UK GDPR Art. 6(1)(f)):</strong> System security, fraud prevention, service reliability, and abuse mitigation.</li>
                <li><strong>Legal Obligation (UK GDPR Art. 6(1)(c)):</strong> Compliance with statutory tax, accounting (HMRC), and financial reporting obligations.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">4. Sub-Processors &amp; Third-Party Transfers</h2>
              <p className="text-base leading-relaxed">We engage trusted third-party service providers bound by strict Data Processing Agreements (DPAs):</p>
              <div className="border-2 border-ink overflow-x-auto">
                <table className="w-full text-left text-sm md:text-base">
                  <thead className="bg-ink text-ground">
                    <tr>
                      <th className="p-3 lab">Sub-Processor</th>
                      <th className="p-3 lab">Role</th>
                      <th className="p-3 lab">Data Transferred</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y-2 divide-ink">
                    <tr><td className="p-3 font-semibold">Stripe Payments UK / US</td><td className="p-3">Payment Processing</td><td className="p-3">Billing details, email, transaction total</td></tr>
                    <tr><td className="p-3 font-semibold">Google Cloud Vertex AI</td><td className="p-3">Script Drafting Engine</td><td className="p-3">Marketing brief, business name, language</td></tr>
                    <tr><td className="p-3 font-semibold">Fal.ai (Veed Fabric)</td><td className="p-3">Avatar Video Synthesis</td><td className="p-3">Portrait photo, approved script audio</td></tr>
                    <tr><td className="p-3 font-semibold">Supabase Inc</td><td className="p-3">Secure Cloud Storage</td><td className="p-3">Encrypted database &amp; video files</td></tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">5. Retention &amp; Biometric Purge Policy</h2>
              <p className="text-base leading-relaxed">
                We believe in strict data minimization. Your uploaded portrait photograph is retained for only 30 days after your order is delivered to facilitate any requested minor touch-ups. After 30 days, the source photograph is permanently deleted from our active storage. Rendered videos remain available in your private dashboard for 90 days.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">6. Your Statutory Rights</h2>
              <p className="text-base leading-relaxed">
                Under UK GDPR, you have the right to: access your personal data; rectify inaccuracies; request erasure (&quot;Right to be Forgotten&quot;); restrict or object to processing; and request data portability. To exercise any right, contact our Data Protection Officer at <a href="mailto:privacy@doppelai.com" className="underline font-semibold">privacy@doppelai.com</a>. You also have the right to lodge a complaint with the UK Information Commissioner&apos;s Office (ICO) at <a href="https://ico.org.uk" target="_blank" rel="noreferrer" className="underline font-semibold">ico.org.uk</a>.
              </p>
            </section>
          </div>
        </div>
      </div>
    </Shell>
  );
}

