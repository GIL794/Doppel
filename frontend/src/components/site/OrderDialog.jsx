import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ImageDrop } from "@/components/site/ImageDrop";
import { LANGUAGES } from "@/components/site/ScriptPreview";
import { useOrder } from "@/context/OrderContext";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { useDemo } from "@/lib/demo";

const fieldCls = "rounded-none border-2 border-ink bg-white h-11 text-base focus-visible:ring-signal";
const EMPTY = {
  name: "",
  email: "",
  company: "",
  language: "English",
  avatar_style: "Looks like me",
  brief: "",
  photo_file_id: null,
  logo_file_id: null,
  consent_terms: false,
  consent_likeness: false,
};

export const OrderDialog = () => {
  const { open, setOpen, prefill } = useOrder();
  const { user } = useAuth();
  const { payments } = useDemo();
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) setForm({ ...EMPTY, name: user?.name || "", email: user?.email || "", ...prefill });
  }, [open, prefill, user]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? (v.target.type === "checkbox" ? v.target.checked : v.target.value) : v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.consent_terms || !form.consent_likeness) {
      toast.error("Please agree to the Terms of Service and Likeness Consent to continue.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/payments/checkout", { ...form, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (err) {
      toast.error(formatApiError(err));
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="rounded-none border-2 border-ink bg-ground shadow-signal-xl max-w-2xl max-h-[92vh] overflow-y-auto p-0" data-testid="order-dialog">
        <div className="bg-ink text-ground px-6 py-5">
          <DialogHeader>
            <DialogTitle className="dsp text-3xl text-ground font-normal">{payments === "closed" ? "Ordering opens soon" : "Your promo video · £350"}</DialogTitle>
            <DialogDescription className="text-ground/80">{payments === "closed" ? "Ordering is not open yet. This form is a preview of the planned order: nothing is charged and no order is created. Planned price £350." : "Tell us the basics. You approve the script before we render."}</DialogDescription>
          </DialogHeader>
        </div>
        <form onSubmit={submit} className="px-6 pb-24 pt-2 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="o-name" className="lab">Your name</Label>
              <Input id="o-name" required value={form.name} onChange={set("name")} className={`${fieldCls} mt-1`} data-testid="order-name-input" />
            </div>
            <div>
              <Label htmlFor="o-email" className="lab">Email</Label>
              <Input id="o-email" type="email" required value={form.email} onChange={set("email")} className={`${fieldCls} mt-1`} data-testid="order-email-input" />
            </div>
            <div>
              <Label htmlFor="o-company" className="lab">Business name</Label>
              <Input id="o-company" required value={form.company} onChange={set("company")} className={`${fieldCls} mt-1`} data-testid="order-company-input" />
            </div>
            <div>
              <Label className="lab">{payments === "closed" ? "Preferred language (planned)" : "Video language"}</Label>
              <Select value={form.language} onValueChange={set("language")}>
                <SelectTrigger className={`${fieldCls} mt-1`} data-testid="order-language-select"><SelectValue /></SelectTrigger>
                <SelectContent className="rounded-none border-2 border-ink">
                  {LANGUAGES.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <p className="lab mb-2">Your avatar</p>
            <RadioGroup value={form.avatar_style} onValueChange={set("avatar_style")} className="grid sm:grid-cols-2 gap-3">
              {["Looks like me", "A new face"].map((v) => (
                <Label key={v} htmlFor={`av-${v}`} className={`flex items-center gap-3 border-2 border-ink p-3 cursor-pointer ${form.avatar_style === v ? "bg-signal" : "bg-white"}`}>
                  <RadioGroupItem id={`av-${v}`} value={v} className="border-ink text-ink" data-testid={`order-avatar-${v === "A new face" ? "new" : "me"}`} />
                  <span className="dsp text-lg font-normal">{v}</span>
                </Label>
              ))}
            </RadioGroup>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <ImageDrop kind="photo" label="Your photo (optional)" value={form.photo_file_id} onChange={set("photo_file_id")} testId="order-photo-upload" />
            <ImageDrop kind="logo" label="Your logo (optional)" value={form.logo_file_id} onChange={set("logo_file_id")} testId="order-logo-upload" />
          </div>
          <div>
            <Label htmlFor="o-brief" className="lab">What should the video say?</Label>
            <Textarea id="o-brief" rows={4} maxLength={3000} value={form.brief} onChange={set("brief")}
              placeholder="Your offer, who it's for, and where people should go. A rough idea is fine."
              className="rounded-none border-2 border-ink bg-white mt-1 text-base focus-visible:ring-signal" data-testid="order-brief-input" />
          </div>

          <div className="space-y-3 border-2 border-ink bg-white p-4">
            <p className="lab text-signal text-xs">Required Consents &amp; Compliance</p>
            <label className="flex items-start gap-3 cursor-pointer text-sm">
              <input
                type="checkbox"
                required
                checked={form.consent_terms}
                onChange={set("consent_terms")}
                className="mt-1 h-4 w-4 rounded-none border-2 border-ink accent-signal text-ink"
                data-testid="order-consent-terms"
              />
              <span className="text-gray-800">
                I agree to the <Link to="/terms" target="_blank" className="underline font-semibold">Terms of Service</Link> and <Link to="/privacy" target="_blank" className="underline font-semibold">Privacy Policy</Link>, and acknowledge that production starts upon my approval of the script.
              </span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer text-sm">
              <input
                type="checkbox"
                required
                checked={form.consent_likeness}
                onChange={set("consent_likeness")}
                className="mt-1 h-4 w-4 rounded-none border-2 border-ink accent-signal text-ink"
                data-testid="order-consent-likeness"
              />
              <span className="text-gray-800">
                I confirm I have all legal rights and consent for the photo/likeness and logo submitted, and understand this generates synthetic AI video for legitimate commercial marketing.
              </span>
            </label>
          </div>

          <button type="submit" disabled={loading || !form.consent_terms || !form.consent_likeness || payments === "unknown" || payments === "closed"}
            className="w-full bg-signal text-ink dsp text-2xl px-6 py-4 border-2 border-ink shadow-hard-md hover:shadow-hard-hover hover:translate-x-1 hover:translate-y-1 transition-[transform,box-shadow] disabled:opacity-70"
            data-testid="order-submit-button">
            {payments === "closed" ? "Ordering opens soon" : loading ? "Opening secure checkout…" : "Continue to payment · £350 →"}
          </button>
          {payments === "real" ? (
            <p className="lab text-center text-graphite">Secure checkout by Stripe · Card & Apple Pay</p>
          ) : payments === "closed" ? (
            <p className="lab text-center text-graphite" data-testid="closed-checkout-note">Ordering is not open yet - nothing is charged and no order is created</p>
          ) : payments === "demo" ? (
            <p className="lab text-center text-graphite" data-testid="demo-checkout-note">Demo checkout - no real payment is taken (Stripe is not connected in this build)</p>
          ) : (
            <p className="lab text-center text-graphite" data-testid="unknown-checkout-note">Payment provider could not be verified - checkout is disabled</p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
};
