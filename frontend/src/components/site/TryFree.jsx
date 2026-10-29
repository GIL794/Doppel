import { useClosed } from "@/lib/demo";
import { Link } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScriptPreview } from "@/components/site/ScriptPreview";
import { useAuth } from "@/context/AuthContext";

const tabCls =
  "rounded-none border-2 border-ink lab px-4 py-3 data-[state=active]:bg-ink data-[state=active]:text-ground data-[state=active]:shadow-none bg-white text-ink";

const TeaserPromo = () => {
  const { user } = useAuth();
  return (
    <div className="grid lg:grid-cols-[1fr_1fr] gap-8 items-center" data-testid="teaser-promo">
      <div>
        <h3 className="dsp text-4xl">Upload a selfie. Hear yourself sell.</h3>
        <p className="mt-4 max-w-md">
          Make a short talking teaser of your own avatar before you buy. Pick one clear photo, type a line, and we animate it.
        </p>
        <ul className="mt-6 space-y-2 lab">
          <li>✓ 2 free teasers per account</li>
          <li>✓ Your voice style, your words</li>
          <li>✓ Saved to your account</li>
        </ul>
        <Link to={user ? "/dashboard" : "/login?next=/dashboard"}
          className="inline-block mt-8 bg-signal text-ink dsp text-xl px-6 py-4 border-2 border-ink shadow-hard-md hover:shadow-hard-hover hover:translate-x-1 hover:translate-y-1 transition-[transform,box-shadow]"
          data-testid="teaser-start-link">
          {user ? "Open the teaser studio →" : "Sign up & make my teaser →"}
        </Link>
      </div>
      <div className="relative mx-auto w-56 aspect-[9/16] bg-ink rounded-[28px] p-2 shadow-signal-xl" aria-hidden="true">
        <div className="w-full h-full rounded-[22px] bg-ground flex flex-col items-center justify-center gap-4 p-4">
          <svg viewBox="0 0 100 100" className="w-24"><circle cx="50" cy="38" r="20" fill="#111" /><path d="M14 100 Q50 46 86 100 Z" fill="#111" /><path className="drw" pathLength="1" d="M42 44 Q50 52 58 44" fill="none" stroke="#ff5a2e" strokeWidth="3" strokeLinecap="round" /></svg>
          <span className="lab bg-signal px-2 py-1">● Speaking</span>
          <span className="mono text-xs text-center">"Hi! Pop in this week…"</span>
        </div>
      </div>
    </div>
  );
};

export const TryFree = () => {
  const closed = useClosed();
  return (
  <section id="try" className="bg-blush py-24 md:py-32 border-y-2 border-ink" data-testid="try-section">
    <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-[200px_1fr] gap-12">
      <p className="lab">Try it free</p>
      <div className="min-w-0">
        <h2 className="dsp h2-xl mb-4">Test drive your video</h2>
        <p className="max-w-xl mb-10">Get a 30-second script for your business in seconds{closed ? ". Talking avatar teasers are not available yet." : ", then hear your own avatar say it."} No card needed.</p>
        <Tabs defaultValue="script">
          <TabsList className="bg-transparent p-0 h-auto gap-3 mb-8 flex-wrap justify-start">
            <TabsTrigger value="script" className={tabCls} data-testid="try-tab-script">1 · Write my script</TabsTrigger>
            {!closed && <TabsTrigger value="teaser" className={tabCls} data-testid="try-tab-teaser">2 · Make a talking teaser</TabsTrigger>}
          </TabsList>
          <TabsContent value="script"><ScriptPreview /></TabsContent>
          <TabsContent value="teaser"><TeaserPromo /></TabsContent>
        </Tabs>
      </div>
    </div>
  </section>
);
};
