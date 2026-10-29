import { Header } from "@/components/site/Header";
import { Hero, Marquee } from "@/components/site/Hero";
import { Samples } from "@/components/site/Samples";
import { HowItWorks, WhyTable, WhoFor } from "@/components/site/Sections";
import { TryFree } from "@/components/site/TryFree";
import { Pricing, Reviews, Faq, FinalCta, Footer } from "@/components/site/Closing";

export default function Landing() {
  return (
    <div className="overflow-x-hidden" data-testid="landing-page">
      <Header />
      <main>
        <Hero />
        <Marquee />
        <Samples />
        <HowItWorks />
        <WhyTable />
        <WhoFor />
        <TryFree />
        <Pricing />
        <Reviews />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
