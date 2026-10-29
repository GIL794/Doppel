import { useEffect, useState } from "react";
import { Shell } from "@/components/site/Shell";
import { TeaserStudio } from "@/components/site/TeaserStudio";
import { useAuth } from "@/context/AuthContext";
import { useOrder } from "@/context/OrderContext";
import { api } from "@/lib/api";

const MyOrders = () => {
  const [orders, setOrders] = useState(null);
  const { openOrder } = useOrder();
  useEffect(() => { api.get("/orders/mine").then(({ data }) => setOrders(data)); }, []);

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
          {orders.map((o) => (
            <div key={o.order_ref} className="p-4 grid sm:grid-cols-4 gap-2 items-center" data-testid={`order-row-${o.order_ref}`}>
              <span className="dsp text-xl">#{o.order_ref}</span>
              <span>{o.company}</span>
              <span className="lab">{new Date(o.created_at).toLocaleDateString("en-GB")}</span>
              <span className="lab bg-signal px-2 py-1 w-fit">In production</span>
            </div>
          ))}
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
