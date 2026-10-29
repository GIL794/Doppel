import { Navigate, BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import ResetPassword from "@/pages/ResetPassword";
import Dashboard from "@/pages/Dashboard";
import Admin from "@/pages/Admin";
import { PaymentSuccess, PaymentCancel } from "@/pages/Payment";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { OrderProvider } from "@/context/OrderContext";
import { OrderDialog } from "@/components/site/OrderDialog";
import { DemoBanner } from "@/components/site/DemoBanner";
import { Loading } from "@/components/site/Shell";

const Protected = ({ children, admin = false }) => {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) return <Loading />;
  if (user === false) return <Navigate to={`/login?next=${location.pathname}`} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
};

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/admin" element={<Protected admin><Admin /></Protected>} />
      <Route path="/payment/success" element={<PaymentSuccess />} />
      <Route path="/payment/cancel" element={<PaymentCancel />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <OrderProvider>
          <AppRouter />
          <OrderDialog />
          <DemoBanner />
          <Toaster position="bottom-center" offset="104px" mobileOffset="104px" toastOptions={{ className: "rounded-none border-2 border-ink font-body" }} />
        </OrderProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
