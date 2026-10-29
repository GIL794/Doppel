import { useEffect, useState } from "react";
import { Shell } from "@/components/site/Shell";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/context/AuthContext";
import { api, fileUrl } from "@/lib/api";
import { useDemo } from "@/lib/demo";

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

  useEffect(() => {
    api.get("/admin/overview").then(({ data }) => setOverview(data));
    api.get("/admin/orders").then(({ data }) => setOrders(data));
  }, []);

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
                {["Ref", "Customer", "Business", "Language / avatar", "Brief", "Files", "Status", "Date"].map((h) => (
                  <TableHead key={h} className="lab text-ground">{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.length === 0 && (
                <TableRow><TableCell colSpan={8} className="text-center py-10" data-testid="admin-orders-empty">No orders yet.</TableCell></TableRow>
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
