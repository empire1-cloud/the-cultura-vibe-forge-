import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/button";
import { LogOut, Hammer, Flame } from "lucide-react";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const linkCls = ({ isActive }) =>
    `px-3 py-2 text-xs uppercase tracking-[0.2em] font-bold transition-colors ${
      isActive ? "text-white" : "text-slate-500 hover:text-slate-200"
    }`;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-slate-100 flex flex-col">
      <header
        className="sticky top-0 z-30 backdrop-blur-xl bg-black/70 border-b border-white/10"
        data-testid="app-header"
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group" data-testid="brand-link">
            <div className="relative h-9 w-9 rounded-sm border border-white/15 flex items-center justify-center bg-gradient-to-b from-slate-200 via-white to-slate-500 group-hover:candy-glow transition-all">
              <Flame className="h-4 w-4 text-[#c8102e]" strokeWidth={2.5} />
            </div>
            <div className="leading-none">
              <div className="font-display font-bold text-[15px] tracking-tight">
                El Arquitecto <span className="candy-text">AI</span>
              </div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">
                Soulfire · Forge
              </div>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            <NavLink to="/dashboard" className={linkCls} data-testid="nav-forge">
              El Centro
            </NavLink>
            <NavLink to="/taller" className={linkCls} data-testid="nav-taller">
              The Taller
            </NavLink>
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-xs text-slate-400 hidden sm:inline" data-testid="user-name">
                  {user.display_name}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-slate-400 hover:text-white hover:bg-transparent"
                  onClick={() => {
                    logout();
                    navigate("/");
                  }}
                  data-testid="logout-button"
                >
                  <LogOut className="h-4 w-4 mr-1.5" />
                  Sign out
                </Button>
              </>
            ) : (
              <>
                <Link to="/login" data-testid="nav-login">
                  <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-white/5">
                    Sign in
                  </Button>
                </Link>
                <Link to="/signup" data-testid="nav-signup">
                  <Button size="sm" className="con-ganas-btn rounded-sm">
                    <Hammer className="h-3.5 w-3.5 mr-1.5" />
                    Start Forging
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-white/10 py-6 text-center text-[11px] uppercase tracking-[0.24em] text-slate-600">
        Hecho con ganas · Creator-owned · {new Date().getFullYear()}
      </footer>
    </div>
  );
}
