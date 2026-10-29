import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Shell, fieldCls, PrimaryBtn } from "@/components/site/Shell";
import { api, formatApiError } from "@/lib/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token: params.get("token"), password });
      toast.success("Password updated. Sign in with your new password.");
      navigate("/login");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell testId="reset-password-page">
      <section className="max-w-md mx-auto px-6 py-24">
        <form onSubmit={submit} className="border-2 border-ink bg-white shadow-signal-lg p-6 space-y-4">
          <h1 className="dsp text-4xl">New password</h1>
          <div>
            <Label htmlFor="np" className="lab">Password (8+ characters)</Label>
            <Input id="np" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} className={`${fieldCls} mt-1`} data-testid="reset-password-input" />
          </div>
          <PrimaryBtn type="submit" disabled={busy} data-testid="reset-password-submit">Save password</PrimaryBtn>
          <Link to="/login" className="lab underline block" data-testid="reset-back-login">Back to sign in</Link>
        </form>
      </section>
    </Shell>
  );
}
