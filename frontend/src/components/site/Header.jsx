import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useOrder } from "@/context/OrderContext";

export const Logo = ({ testId = "brand-logo" }) => (
  <Link to="/" className="flex items-center gap-2" data-testid={testId}>
    <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
      <rect x="2" y="2" width="28" height="28" fill="#111" />
      <circle cx="12" cy="14" r="5" fill="#ff5a2e" />
      <circle cx="20" cy="14" r="5" fill="none" stroke="#f7f5ef" strokeWidth="2" />
      <path d="M10 23h12" stroke="#f7f5ef" strokeWidth="2" />
    </svg>
    <span className="dsp text-2xl">DoppelAI</span>
  </Link>
);

const NAV = [
  ["#samples", "Samples"],
  ["#how", "How it works"],
  ["#try", "Try free"],
  ["#why", "Why us"],
  ["#pricing", "Pricing"],
  ["#faq", "FAQ"],
];

export const Header = () => {
  const { user } = useAuth();
  const { openOrder } = useOrder();
  return (
    <header className="sticky top-0 z-50 bg-ground/95 backdrop-blur border-b-2 border-ink" data-testid="site-header">
      <nav className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-4" aria-label="Main">
        <Logo />
        <div className="hidden lg:flex gap-7 lab">
          {NAV.map(([href, label]) => (
            <a key={href} href={href} className="link-grow" data-testid={`nav-${href.slice(1)}`}>{label}</a>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <Link
            to={user ? (user.role === "admin" ? "/admin" : "/dashboard") : "/login"}
            className="lab link-grow hidden sm:inline"
            data-testid="nav-account-link"
          >
            {user ? "My account" : "Sign in"}
          </Link>
          <button
            type="button"
            onClick={() => openOrder()}
            className="lab bg-ink text-ground px-4 py-2 rounded-full hover:bg-signal hover:text-ink transition-colors"
            data-testid="header-buy-button"
          >
            Buy · £350
          </button>
        </div>
      </nav>
      <div className="lg:hidden border-t border-ink/20 overflow-x-auto">
        <div className="flex gap-6 px-6 py-2 lab whitespace-nowrap">
          {NAV.map(([href, label]) => (
            <a key={href} href={href} data-testid={`mnav-${href.slice(1)}`}>{label}</a>
          ))}
          <Link to={user ? "/dashboard" : "/login"} data-testid="mnav-account">{user ? "Account" : "Sign in"}</Link>
        </div>
      </div>
    </header>
  );
};
