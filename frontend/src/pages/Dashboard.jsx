import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Shell } from "@/components/site/Shell";
import { TeaserStudio } from "@/components/site/TeaserStudio";
import { useAuth } from "@/context/AuthContext";
import { useOrder } from "@/context/OrderContext";
import { api, formatApiError, fileUrl } from "@/lib/api";

const STATUS_LABELS = {
  in_production: "In production",
  drafting: "Drafting your script",
  script_ready: "Script ready - review it",
  changes_requested: "Changes requested",
  script_approved: "Script approved - rendering",
  delivered: "Delivered",
};

const OrderCard = ({ order: o, onChanged }) => {
  const [changes, setChanges] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const act = async (path, body) => {
    setBusy(true);
    try {
      await api.post(path, body || {});
      onChanged();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-4" data-testid={`order-row-${o.order_ref}`}>
      <div className="grid sm:grid-cols-4 gap-2 items-center">
        <span className="dsp text-xl">#{o.order_ref}</span>
        <span>{o.company}</span>
        <span className="lab">{new Date(o.created_at).toLocaleDateString("en-GB")}</span>
        <span className={`lab px-2 py-1 w-fit ${o.production_status === "delivered" ? "bg-ink text-ground" : "bg-signal"}`} data-testid={`order-status-${o.order_ref}`}>
          {STATUS_LABELS[o.production_status] || "In production"}
        </span>
      </div>
      {o.script_text && (
        <div className="mt-4 border-2 border-ink p-4 bg-ground" data-testid={`order-script-${o.order_ref}`}>
          <p className="lab mb-2">Your script</p>
          <p className="whitespace-pre-wrap">{o.script_text}</p>
        </div>
      )}
      {o.production_status === "script_ready" && !changes && (
        <div className="mt-3 flex flex-wrap gap-3">
          <button type="button" disabled={busy}
            onClick={() => act(`/orders/${o.order_ref}/script/approve`)}
            className="lab bg-ink text-ground px-4 py-2 hover:bg-signal hover:text-ink transition-colors"
            data-testid={`approve-script-${o.order_ref}`}>Approve script</button>
          <button type="button" onClick={() => setChanges(true)}
            className="lab border-2 border-ink px-4 py-2 hover:bg-blush transition-colors"
            data-testid={`request-changes-${o.order_ref}`}>Request changes</button>
        </div>
      )}
      {o.production_status === "script_ready" && changes && (
        <div className="mt-3 space-y-2">
          <textarea className="w-full border-2 border-ink p-3" rows={3} value={note}
            onChange={(e) => setNote(e.target.value)} placeholder="What should change?"
            data-testid={`changes-note-${o.order_ref}`} />
          <div className="flex gap-3">
            <button type="button" disabled={busy || note.trim().length < 3}
              onClick={() => act(`/orders/${o.order_ref}/script/changes`, { note })}
              className="lab bg-ink text-ground px-4 py-2 hover:bg-signal hover:text-ink transition-colors disabled:opacity-40"
              data-testid={`send-changes-${o.order_ref}`}>Send changes</button>
            <button type="button" onClick={() => setChanges(false)} className="lab underline">Back</button>
          </div>
        </div>
      )}
      {o.production_status === "changes_requested" && o.change_note && (
        <p className="mt-3 text-sm" data-testid={`changes-sent-${o.order_ref}`}>Changes sent to the studio: {o.change_note}</p>
      )}
      {o.production_status === "delivered" && o.delivered_note && (
        <p className="mt-3" data-testid={`delivery-note-${o.order_ref}`}>{o.delivered_note}</p>
      )}
      {o.production_status !== "delivered" && o.video_job === "failed" && (
        <p className="mt-3" data-testid={`render-failed-${o.order_ref}`}>
          Rendering hit a problem - the studio has been notified and will sort it for you.
        </p>
      )}
      {o.production_status === "delivered" && o.video_file_id && (
        <div className="mt-4" data-testid={`order-video-${o.order_ref}`}>
          <video controls preload="metadata" className="w-full max-w-md border-2 border-ink bg-ink"
            src={fileUrl(o.video_file_id)} />
          <a href={fileUrl(o.video_file_id)} download className="lab underline mt-2 inline-block"
            data-testid={`download-video-${o.order_ref}`}>Download your video</a>
        </div>
      )}
    </div>
  );
};

const MyOrders = () => {
  const [orders, setOrders] = useState(null);
  const { openOrder } = useOrder();
  const load = useCallback(() => { api.get("/orders/mine").then(({ data }) => setOrders(data)); }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <section className="mt-16" data-testid="my-orders">
      <div className="flex flex-wrap justify-between items-end gap-4 mb-6">
        <h2 className="dsp h2-xl">My videos</h2>
        <button type="button" onClick={() => openOrder()} className="lab bg-ink text-ground px-4 py-3 hover:bg-signal hover:text-ink transition-colors" data-testid="dashboard-order-button">
          Order a video · £350
        </button>
      </div>
      {orders && orders.length === 0 && (
        <div className="border-2 border-dashed border-ink p-10" data-testid="orders-empty">
          <p className="dsp text-2xl">No paid orders yet.</p>
          <p className="mt-2">Love your teaser? Order the full video and we'll take it from there.</p>
        </div>
      )}
      {orders && orders.length > 0 && (
        <div className="border-2 border-ink divide-y-2 divide-ink bg-white">
          {orders.map((o) => <OrderCard key={o.order_ref} order={o} onChanged={load} />)}
        </div>
      )}
    </section>
  );
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  return (
    <Shell testId="dashboard-page">
      <div className="max-w-6xl mx-auto px-6 py-12 md:py-16">
        <div className="flex flex-wrap justify-between items-end gap-4 mb-10">
          <div>
            <p className="lab mb-2">Hi, {user.name}</p>
            <h1 className="dsp h1-xl">Your studio</h1>
          </div>
          <button type="button" onClick={logout} className="lab underline" data-testid="logout-button">Sign out</button>
        </div>
        <TeaserStudio />
        <MyOrders />
      </div>
    </Shell>
  );
}

