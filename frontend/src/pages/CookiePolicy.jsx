import { Shell } from "@/components/site/Shell";

export default function CookiePolicy() {
  return (
    <Shell testId="cookie-policy-page">
      <div className="bg-ground py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-6">
          <div className="border-2 border-ink bg-white p-8 md:p-12 shadow-signal-lg space-y-8">
            <div>
              <p className="lab text-signal mb-2">Legal & Compliance</p>
              <h1 className="dsp text-4xl md:text-5xl">Cookie Policy</h1>
              <p className="lab text-graphite mt-2">Effective Date: November 2, 2026 · UK Privacy &amp; Electronic Communications Regulations (PECR)</p>
            </div>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">1. What Are Cookies?</h2>
              <p className="text-base leading-relaxed">
                Cookies are small text files placed on your computer or device when you browse websites. They are commonly used to make websites work properly, provide a secure login state, and ensure transactional operations can proceed.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">2. Our Minimal, Privacy-First Approach</h2>
              <p className="text-base leading-relaxed">
                At DoppelAI, we operate on a strict privacy-by-design architecture. <strong>We do not use third-party tracking, behavioral advertising, cross-site targeting, or non-essential profiling cookies.</strong>
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">3. Cookies We Deploy (Strictly Necessary Only)</h2>
              <p className="text-base leading-relaxed">
                Under UK PECR and GDPR, strictly necessary cookies that are required to operate the service do not require prior consent, but must be clearly explained:
              </p>
              <div className="border-2 border-ink overflow-x-auto">
                <table className="w-full text-left text-sm md:text-base">
                  <thead className="bg-ink text-ground">
                    <tr>
                      <th className="p-3 lab">Cookie Name</th>
                      <th className="p-3 lab">Purpose</th>
                      <th className="p-3 lab">Duration</th>
                      <th className="p-3 lab">Security Properties</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y-2 divide-ink">
                    <tr>
                      <td className="p-3 font-mono font-semibold">access_token</td>
                      <td className="p-3">Authenticates your active API session for dashboard and admin access.</td>
                      <td className="p-3">15 minutes</td>
                      <td className="p-3">HttpOnly; SameSite=Lax; Secure</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-mono font-semibold">refresh_token</td>
                      <td className="p-3">Rotates and renews your login session securely without re-entering credentials.</td>
                      <td className="p-3">14 days</td>
                      <td className="p-3">HttpOnly; SameSite=Lax; Secure</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-mono font-semibold">oauth_state</td>
                      <td className="p-3">Prevents Cross-Site Request Forgery (CSRF) during Google OAuth sign-in.</td>
                      <td className="p-3">10 minutes</td>
                      <td className="p-3">HttpOnly; SameSite=Lax; Secure</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-mono font-semibold">doppel_cookie_consent</td>
                      <td className="p-3">Stores your dismissal preference for the cookie notice banner (localStorage).</td>
                      <td className="p-3">Persistent (1 year)</td>
                      <td className="p-3">Local Storage key</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">4. Managing &amp; Disabling Cookies</h2>
              <p className="text-base leading-relaxed">
                You can block or delete cookies through your web browser settings at any time (e.g., in Chrome, Safari, Firefox, or Edge). Please note that if you disable strictly necessary authentication cookies, you will not be able to log in, review scripts, or access your customer dashboard.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="dsp text-2xl">5. Questions &amp; Inquiries</h2>
              <p className="text-base leading-relaxed">
                For questions regarding our cookie practices, contact our team at <a href="mailto:privacy@doppelai.com" className="underline font-semibold">privacy@doppelai.com</a>.
              </p>
            </section>
          </div>
        </div>
      </div>
    </Shell>
  );
}

