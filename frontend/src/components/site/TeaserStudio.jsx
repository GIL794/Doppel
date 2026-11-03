import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ImageDrop } from "@/components/site/ImageDrop";
import { PrimaryBtn, fieldCls } from "@/components/site/Shell";
import { api, fileUrl, formatApiError } from "@/lib/api";

const TeaserCard = ({ t }) => (
  <div className="border-2 border-ink bg-white p-3 flex flex-col gap-3" data-testid={`teaser-card-${t.teaser_id}`}>
    <div className="aspect-square bg-ink flex items-center justify-center overflow-hidden">
      {t.status === "ready" && (
        <video src={fileUrl(t.video_file_id)} controls playsInline className="w-full h-full object-contain" data-testid="teaser-video" />
      )}
      {t.status === "processing" && <span className="lab text-signal animate-pulse">● Animating your avatar…</span>}
      {t.status === "failed" && <span className="lab text-ground px-4 text-center">{t.error || "Generation failed"}</span>}
    </div>
    <p className="text-sm line-clamp-2">“{t.text}”</p>
    <span className="lab text-graphite" data-testid="teaser-status">{t.status === "ready" ? "Ready ✓" : t.status}</span>
  </div>
);

export const TeaserStudio = () => {
  const [photo, setPhoto] = useState(null);
  const [text, setText] = useState(() => sessionStorage.getItem("doppel_teaser_line") || "");
  const [voice, setVoice] = useState("");
  const [data, setData] = useState({ items: [], remaining: 0 });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const { data: d } = await api.get("/teasers");
    setData(d);
    return d;
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!data.items.some((t) => t.status === "processing")) return undefined;
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [data, load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!photo) return toast.error("Upload a clear, front-facing photo first");
    setBusy(true);
    try {
      await api.post("/teasers", { photo_file_id: photo, text, voice_description: voice || null });
      sessionStorage.removeItem("doppel_teaser_line");
      toast.success("Your avatar is warming up. This takes a minute or two.");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="grid lg:grid-cols-[1fr_1.3fr] gap-8" data-testid="teaser-studio">
      <form onSubmit={submit} className="border-2 border-ink bg-white shadow-signal-lg p-6 space-y-4 h-fit">
        <div className="flex justify-between items-baseline">
          <h2 className="dsp text-3xl">Teaser studio</h2>
          <span className="lab" data-testid="teaser-remaining">{data.remaining} free left</span>
        </div>
        <ImageDrop kind="photo" label="Front-facing photo" value={photo} onChange={setPhoto} testId="teaser-photo-upload" />
        <div>
          <Label htmlFor="t-text" className="lab">What should your avatar say? ({text.length}/180)</Label>
          <Textarea id="t-text" rows={3} required minLength={5} maxLength={180} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Hi! I'm Sam from Bloom Florist. Fresh bouquets, same-day delivery. Pop in this week!"
            className="rounded-none border-2 border-ink bg-white mt-1 text-base focus-visible:ring-signal" data-testid="teaser-text-input" />
        </div>
        <div>
          <Label htmlFor="t-voice" className="lab">Voice style (optional)</Label>
          <Input id="t-voice" maxLength={120} value={voice} onChange={(e) => setVoice(e.target.value)} placeholder="e.g. Warm, British accent"
            className={`${fieldCls} mt-1`} data-testid="teaser-voice-input" />
        </div>
        <p className="lab text-xs text-graphite border-t border-ink/20 pt-3">
          ✦ Synthetic Media Notice: Generating a teaser produces synthetic AI video. By submitting, you confirm you hold all likeness rights for the uploaded portrait.
        </p>
        <PrimaryBtn type="submit" disabled={busy || data.remaining < 1} data-testid="teaser-generate-button">
          {busy ? "Sending…" : data.remaining < 1 ? "Free teasers used" : "Make my talking teaser →"}
        </PrimaryBtn>
      </form>
      <div>
        <p className="lab mb-4">Your teasers</p>
        {data.items.length === 0 ? (
          <div className="border-2 border-dashed border-ink p-10 text-center" data-testid="teaser-empty">
            <p className="dsp text-2xl">No teasers yet.</p>
            <p className="mt-2">Upload a photo and type a line to hear your avatar.</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">{data.items.map((t) => <TeaserCard key={t.teaser_id} t={t} />)}</div>
        )}
      </div>
    </section>
  );
};
