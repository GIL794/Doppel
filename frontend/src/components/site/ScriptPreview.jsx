import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { API } from "@/lib/api";
import { useOrder } from "@/context/OrderContext";

export const LANGUAGES = ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Dutch", "Arabic", "Hindi", "Chinese"];
const VIBES = ["Fun & upbeat", "Warm & friendly", "Bold & punchy", "Calm & premium"];

export const parseScript = (text) => {
  const pick = (label) => {
    const m = text.match(new RegExp(`${label}:\\s*([\\s\\S]*?)(?=\\n\\s*(HOOK|SCRIPT|CTA):|$)`));
    return m ? m[1].trim() : "";
  };
  return { hook: pick("HOOK"), script: pick("SCRIPT"), cta: pick("CTA") };
};

async function streamScript(body, onDelta) {
  const res = await fetch(`${API}/script/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Please describe your business in a few words.");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const p of parts) {
      if (!p.startsWith("data: ")) continue;
      const ev = JSON.parse(p.slice(6));
      if (ev.error) throw new Error(ev.error);
      if (ev.delta) onDelta(ev.delta);
    }
  }
}

const fieldCls = "rounded-none border-2 border-ink bg-white h-12 text-base focus-visible:ring-signal";

export const ScriptPreview = () => {
  const [form, setForm] = useState({ business: "", offer: "", language: "English", vibe: VIBES[0] });
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const { openOrder } = useOrder();
  const navigate = useNavigate();
  const parsed = parseScript(text);
  const done = !loading && text;

  const generate = async (e) => {
    e.preventDefault();
    setText("");
    setLoading(true);
    try {
      await streamScript(form, (d) => setText((t) => t + d));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const makeTeaser = () => {
    sessionStorage.setItem("doppel_teaser_line", (parsed.hook || "").slice(0, 180));
    navigate("/dashboard");
  };

  return (
    <div className="grid lg:grid-cols-2 gap-8" data-testid="script-preview">
      <form onSubmit={generate} className="space-y-5">
        <div>
          <Label htmlFor="biz" className="lab">Your business</Label>
          <Input id="biz" required minLength={2} maxLength={300} value={form.business} className={`${fieldCls} mt-2`}
            placeholder="e.g. Family bakery in Leeds" onChange={(e) => setForm({ ...form, business: e.target.value })}
            data-testid="script-business-input" />
        </div>
        <div>
          <Label htmlFor="offer" className="lab">What to promote (optional)</Label>
          <Input id="offer" maxLength={300} value={form.offer} className={`${fieldCls} mt-2`}
            placeholder="e.g. our new sourdough range" onChange={(e) => setForm({ ...form, offer: e.target.value })}
            data-testid="script-offer-input" />
        </div>
        <div>
          <Label className="lab">Language</Label>
          <Select value={form.language} onValueChange={(v) => setForm({ ...form, language: v })}>
            <SelectTrigger className={`${fieldCls} mt-2`} data-testid="script-language-select"><SelectValue /></SelectTrigger>
            <SelectContent className="rounded-none border-2 border-ink">
              {LANGUAGES.map((l) => <SelectItem key={l} value={l} data-testid={`script-lang-${l}`}>{l}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <p className="lab mb-2">Vibe</p>
          <div className="flex flex-wrap gap-2">
            {VIBES.map((v) => (
              <button type="button" key={v} onClick={() => setForm({ ...form, vibe: v })}
                className={`lab px-3 py-2 border-2 border-ink transition-colors ${form.vibe === v ? "bg-ink text-ground" : "bg-white hover:bg-signal"}`}
                data-testid={`script-vibe-${v.split(" ")[0].toLowerCase()}`}>{v}</button>
            ))}
          </div>
        </div>
        <button type="submit" disabled={loading}
          className="w-full bg-ink text-ground dsp text-2xl px-6 py-4 border-2 border-ink shadow-signal-lg hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-[transform,box-shadow] disabled:opacity-70"
          data-testid="script-generate-button">
          {loading ? "Writing your script…" : "Write my free script →"}
        </button>
      </form>

      <div className="border-2 border-ink bg-ink text-ground p-6 min-h-[360px] flex flex-col" data-testid="script-output">
        <div className="flex justify-between lab mb-4"><span className="text-signal">● Teleprompter</span><span>~30 sec</span></div>
        {!text && !loading && (
          <p className="dsp text-3xl text-ground/40 my-auto">Your script appears here, live.</p>
        )}
        {(text || loading) && (
          <div className="space-y-4 flex-1">
            {parsed.hook && <p className="dsp text-3xl text-signal" data-testid="script-hook">{parsed.hook}</p>}
            <p className={`whitespace-pre-wrap ${loading ? "caret" : ""}`} data-testid="script-body">
              {parsed.script || (parsed.hook ? "" : text)}
            </p>
            {parsed.cta && <p className="lab border-t border-ground/30 pt-3" data-testid="script-cta">CTA · {parsed.cta}</p>}
          </div>
        )}
        {done && (
          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <button type="button" onClick={() => openOrder({ company: form.business, language: form.language, brief: text })}
              className="flex-1 bg-signal text-ink dsp text-xl px-4 py-3 border-2 border-ground hover:bg-ground transition-colors"
              data-testid="script-order-button">Turn into my video · £350</button>
            <button type="button" onClick={makeTeaser}
              className="flex-1 lab border-2 border-ground px-4 py-3 hover:bg-ground hover:text-ink transition-colors"
              data-testid="script-teaser-button">Hear my avatar say it (free)</button>
          </div>
        )}
      </div>
    </div>
  );
};
