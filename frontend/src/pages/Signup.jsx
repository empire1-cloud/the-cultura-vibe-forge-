import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

export default function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", display_name: "" });
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await signup(form.email, form.password, form.display_name);
      toast.success("The forge is hot. Let's build.");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-8rem)] grid lg:grid-cols-2">
      <div className="flex items-center justify-center p-8 lg:p-16 order-2 lg:order-1">
        <form
          onSubmit={onSubmit}
          className="w-full max-w-sm space-y-6"
          data-testid="signup-form"
        >
          <div>
            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">
              Create account
            </div>
            <h1 className="font-display font-bold text-3xl tracking-tight">Forge your name</h1>
            <p className="mt-2 text-sm text-slate-500">
              Your artifacts will be stored in The Taller — creator-owned.
            </p>
          </div>

          <div className="space-y-5">
            <div>
              <label className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                Display name
              </label>
              <input
                required
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                className="mt-2 w-full bg-transparent border-b border-slate-700 focus:border-[#c8102e] outline-none py-3 text-white"
                data-testid="signup-name-input"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                Email
              </label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="mt-2 w-full bg-transparent border-b border-slate-700 focus:border-[#c8102e] outline-none py-3 text-white"
                data-testid="signup-email-input"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                Password · min 6
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="mt-2 w-full bg-transparent border-b border-slate-700 focus:border-[#c8102e] outline-none py-3 text-white"
                data-testid="signup-password-input"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full con-ganas-btn rounded-sm h-11"
            data-testid="signup-submit-button"
          >
            {loading ? "Firing up..." : "Light the Forge"}
          </Button>

          <div className="text-xs text-slate-500">
            Already on the crew?{" "}
            <Link to="/login" className="text-slate-200 hover:text-white underline underline-offset-4">
              Sign in
            </Link>
          </div>
        </form>
      </div>

      <div className="relative hidden lg:flex items-end p-16 border-l border-white/5 overflow-hidden order-1 lg:order-2">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url(https://images.pexels.com/photos/33604975/pexels-photo-33604975.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)",
            filter: "grayscale(0.4) contrast(1.1) brightness(0.5)",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-tl from-black/70 via-black/40 to-[#c8102e]/25" />
        <div className="relative z-10 max-w-md ml-auto text-right">
          <div className="text-[10px] uppercase tracking-[0.35em] text-slate-400 mb-4">
            Soulfire · DNA · Equity
          </div>
          <h2 className="font-display font-bold text-4xl leading-tight tracking-tight">
            Build like a <span className="candy-text">custom shop.</span>
          </h2>
          <p className="mt-4 text-slate-300 text-sm leading-relaxed">
            Not a tech startup. Every detail chrome, every line intentional.
          </p>
        </div>
      </div>
    </div>
  );
}
