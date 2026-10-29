import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Shell, fieldCls, PrimaryBtn } from "@/components/site/Shell";
import { useAuth, startGoogleLogin } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";

const tabCls = "flex-1 rounded-none lab py-3 data-[state=active]:bg-ink data-[state=active]:text-ground data-[state=active]:shadow-none";

const Field = ({ id, label, ...props }) => (
  <div>
    <Label htmlFor={id} className="lab">{label}</Label>
    <Input id={id} className={`${fieldCls} mt-1`} {...props} />
  </div>
);

const GoogleButton = ({ next }) => (
  <button type="button" onClick={() => startGoogleLogin(next)}
    className="w-full flex items-center justify-center gap-3 border-2 border-ink bg-white py-3 lab hover:bg-blush transition-colors"
    data-testid="google-login-button">
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.6 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.8 6C12.4 13.6 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.1 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17z"/><path fill="#FBBC05" d="M10.5 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.8-6A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.7l7.9-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.3-8.5 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6C6.6 42.6 14.6 48 24 48z"/></svg>
    Continue with Google
  </button>
);

export default function Login() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") || "/dashboard";
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) navigate(user.role === "admin" && next === "/dashboard" ? "/admin" : next, { replace: true });
  }, [user, navigate, next]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "forgot") {
        await api.post("/auth/forgot-password", { email: form.email, origin_url: window.location.origin });
        toast.success("If that email has an account, a reset link is on its way.");
        setMode("signin");
      } else {
        const path = mode === "signup" ? "/auth/register" : "/auth/login";
        const body = mode === "signup" ? form : { email: form.email, password: form.password };
        const { data } = await api.post(path, body);
        setUser(data);
        toast.success(mode === "signup" ? "Welcome to DoppelAI!" : "Welcome back!");
      }
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell testId="login-page">
      <section className="max-w-6xl mx-auto px-6 py-16 md:py-24 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="lab mb-4">Your account</p>
          <h1 className="dsp h1-xl">Meet your<br />digital double.</h1>
          <p className="mt-6 max-w-md">Sign in to make free talking teasers of your avatar, and track every video you order.</p>
        </div>
        <div className="border-2 border-ink bg-white shadow-signal-lg p-6" data-testid="auth-card">
          {mode === "forgot" ? (
            <form onSubmit={submit} className="space-y-4">
              <h2 className="dsp text-3xl">Reset password</h2>
              <Field id="f-email" label="Email" type="email" required value={form.email} onChange={set("email")} data-testid="forgot-email-input" />
              <PrimaryBtn type="submit" disabled={busy} data-testid="forgot-submit-button">Send reset link</PrimaryBtn>
              <button type="button" className="lab underline" onClick={() => setMode("signin")} data-testid="back-to-signin">Back to sign in</button>
            </form>
          ) : (
            <Tabs value={mode} onValueChange={setMode}>
              <TabsList className="w-full rounded-none border-2 border-ink p-0 h-auto bg-ground">
                <TabsTrigger value="signin" className={tabCls} data-testid="auth-tab-signin">Sign in</TabsTrigger>
                <TabsTrigger value="signup" className={tabCls} data-testid="auth-tab-signup">Create account</TabsTrigger>
              </TabsList>
              {["signin", "signup"].map((m) => (
                <TabsContent key={m} value={m}>
                  <form onSubmit={submit} className="space-y-4 pt-4">
                    {m === "signup" && <Field id="s-name" label="Your name" required value={form.name} onChange={set("name")} data-testid="signup-name-input" />}
                    <Field id={`${m}-email`} label="Email" type="email" required value={form.email} onChange={set("email")} data-testid={`${m}-email-input`} />
                    <Field id={`${m}-pw`} label="Password" type="password" required minLength={m === "signup" ? 8 : 1} value={form.password} onChange={set("password")} data-testid={`${m}-password-input`} />
                    <PrimaryBtn type="submit" disabled={busy} data-testid={`${m}-submit-button`}>
                      {busy ? "One sec…" : m === "signup" ? "Create my account →" : "Sign in →"}
                    </PrimaryBtn>
                    {m === "signin" && (
                      <button type="button" className="lab underline" onClick={() => setMode("forgot")} data-testid="forgot-password-link">Forgot password?</button>
                    )}
                  </form>
                </TabsContent>
              ))}
            </Tabs>
          )}
          <div className="flex items-center gap-3 my-5 lab text-graphite"><span className="flex-1 h-px bg-ink/30" />or<span className="flex-1 h-px bg-ink/30" /></div>
          <GoogleButton next={next} />
          <p className="lab text-center mt-5"><Link to="/" className="underline" data-testid="login-back-home">← Back to site</Link></p>
        </div>
      </section>
    </Shell>
  );
}
