import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Shell } from "@/components/site/Shell";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/context/AuthContext";
import { api, fileUrl, formatApiError } from "@/lib/api";
import { useDemo } from "@/lib/demo";

const PRODUCTION_LABELS = {
  awaiting_payment: "Awaiting payment",
  in_production: "In production",
  script_ready: "Script sent",
  changes_requested: "Changes requested",
  script_approved: "Script approved",
  delivered: "Delivered",
};

const ProductionCell = ({ order: o, onChanged }) => {
  const [open, setOpen] = useState(null); // "script" | "deliver"
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const send = async (path, body) => {
    setBusy(true);
    try {
      const { data } = await api.post(path, body);
      toast.success(data.email_sent ? "Saved and customer emailed." : "Saved. Customer email not configured (SMTP off).");
      setOpen(null);
      setText("");
      onChanged();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2" data-testid={`production-${o.order_ref}`}>
      <span className={`lab px-2 py-1 ${o.production_status === "delivered" ? "bg-ink text-ground" : "bg-ground border border-ink"}`}>
        {PRODUCTION_LABELS[o.production_status] || o.production_status || "-"}
      </span>
      {o.production_status === "changes_requested" && o.change_note && (
        <p className="text-sm max-w-xs" data-testid={`admin-changes-${o.order_ref}`}>Customer asked: {o.change_note}</p>
      )}
      {["in_production", "changes_requested"].includes(o.production_status) && (
        open === "script" ? (
          <div className="space-y-2">
            <textarea className="w-64 border-2 border-ink p-2 text-sm" rows={4} value={text}
              onChange={(e) => setText(e.target.value)} placeholder="Script for the customer to approve"
              data-testid={`admin-script-input-${o.order_ref}`} />
            <div className="flex gap-2">
              <button type="button" disabled={busy || text.trim().length < 10}
                onClick={() => send(`/admin/orders/${o.order_ref}/script`, { script_text: text })}
                className="lab bg-ink text-ground px-3 py-1 disabled:opacity-40"
                data-testid={`admin-send-script-${o.order_ref}`}>Send script</button>
              <button type="button" onClick={() => setOpen(null)} className="lab underline">Cancel</button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setOpen("script")} className="lab underline"
            data-testid={`admin-open-script-${o.order_ref}`}>Send script for approval</button>
        )
      )}
      {o.production_status === "script_approved" && (
        open === "deliver" ? (
          <div className="space-y-2">
            <input className="w-64 border-2 border-ink p-2 text-sm" value={text}
              onChange={(e) => setText(e.target.value)} placeholder="Delivery note (optional)"
              data-testid={`admin-deliver-input-${o.order_ref}`} />
            <div className="flex gap-2">
              <button type="button" disabled={busy}
                onClick={() => send(`/admin/orders/${o.order_ref}/deliver`, { note: text })}
                className="lab bg-ink text-ground px-3 py-1 disabled:opacity-40"
                data-testid={`admin-deliver-${o.order_ref}`}>Mark delivered</button>
              <button type="button" onClick={() => setOpen(null)} className="lab underline">Cancel</button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setOpen("deliver")} className="lab underline"
            data-testid={`admin-open-deliver-${o.order_ref}`}>Mark delivered</button>
        )
      )}
    </div>
  );
};

const STATS = [
  ["revenue_gbp", "Revenue", (v) => `£${v.toLocaleString("en-GB")}`],
  ["paid_orders", "Paid orders"],
  ["started_checkouts", "Checkouts started"],
  ["customers", "Accounts"],
  ["teasers", "Teasers made"],
  ["scripts", "Free scripts"],
];

const FileLink = ({ id, label }) =>
  id ? <a href={fileUrl(id)} target="_blank" rel="noreferrer" className="underline lab" data-testid={`admin-file-${id}`}>{label}</a> : <span className="text-graphite">—</span>;

export default function Admin() {
  const { logout } = useAuth();
  const { payments } = useDemo();
  const [overview, setOverview] = useState(null);
  const [orders, setOrders] = useState([]);

  const load = useCallback(() => {
    api.get("/admin/overview").then(({ data }) => setOverview(data));
    api.get("/admin/orders").then(({ data }) => setOrders(data));
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <Shell testId="admin-page">
      <div className="max-w-6xl mx-auto px-6 py-12 md:py-16">
        <div className="flex flex-wrap justify-between items-end gap-4 mb-10">
          <h1 className="dsp h1-xl">Orders desk</h1>
          {payments !== "real" && (
            <span className="lab bg-ground border-2 border-ink px-3 py-2" data-testid="demo-admin-note">
              {payments === "demo"
                ? "LOCAL DEMO - revenue and orders shown are simulated, no real payments"
                : "LOCAL DEMO - payment provider unverified; treat revenue as not real"}
            </span>
          )}
          <button type="button" onClick={logout} className="lab underline" data-testid="admin-logout-button">Sign out</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-12">
          {STATS.map(([k, label, fmt]) => (
            <div key={k} className="border-2 border-ink bg-white p-4" data-testid={`admin-stat-${k}`}>
              <p className="lab text-graphite">{label}</p>
              <p className="dsp text-3xl tab mt-1">{overview ? (fmt ? fmt(overview[k]) : overview[k]) : "…"}</p>
            </div>
          ))}
        </div>
        <div className="border-2 border-ink bg-white overflow-x-auto">
          <Table>
            <TableHeader className="bg-ink">
              <TableRow className="hover:bg-ink">
                {["Ref", "Customer", "Business", "Language / avatar", "Brief", "Files", "Payment", "Production", "Date"].map((h) => (
                  <TableHead key={h} className="lab text-ground">{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.length === 0 && (
                <TableRow><TableCell colSpan={9} className="text-center py-10" data-testid="admin-orders-empty">No orders yet.</TableCell></TableRow>
              )}
              {orders.map((o) => (
                <TableRow key={o.session_id || o.order_ref} className="border-b border-ink/20 align-top" data-testid={`admin-order-${o.order_ref}`}>
                  <TableCell className="dsp text-lg">#{o.order_ref}</TableCell>
                  <TableCell><div>{o.name}</div><div className="text-sm text-graphite">{o.email}</div></TableCell>
                  <TableCell>{o.company}</TableCell>
                  <TableCell className="text-sm">{o.language}<br />{o.avatar_style}</TableCell>
                  <TableCell className="text-sm max-w-xs"><p className="line-clamp-3 whitespace-pre-wrap">{o.brief || "—"}</p></TableCell>
                  <TableCell className="space-x-2"><FileLink id={o.photo_file_id} label="Photo" /><FileLink id={o.logo_file_id} label="Logo" /></TableCell>
                  <TableCell>
                    <span className={`lab px-2 py-1 ${o.payment_status === "paid" ? "bg-signal" : "bg-ground border border-ink"}`}>{o.payment_status}</span>
                  </TableCell>
                  <TableCell><ProductionCell order={o} onChanged={load} /></TableCell>
                  <TableCell className="lab whitespace-nowrap">{new Date(o.created_at).toLocaleDateString("en-GB")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </Shell>
  );
}
