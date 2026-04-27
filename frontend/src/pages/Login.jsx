import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back to the forge.");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-8rem)] grid lg:grid-cols-2">
      <div className="relative hidden lg:flex items-end p-16 border-r border-white/5 overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url(https://images.pexels.com/photos/4829063/pexels-photo-4829063.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)",
            filter: "grayscale(0.6) contrast(1.1) brightness(0.45)",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-black/70 via-black/50 to-[#c8102e]/20" />
        <div className="relative z-10 max-w-md">
          <div className="text-[10px] uppercase tracking-[0.35em] text-slate-400 mb-4">
            El Arquitecto AI
          </div>
          <h2 className="font-display font-bold text-4xl leading-tight tracking-tight">
            Return to <span className="candy-text">the forge.</span>
          </h2>
          <p className="mt-4 text-slate-300 text-sm leading-relaxed">
            Your artifacts are waiting in The Taller. Same soulfire. Same chrome.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center p-8 lg:p-16">
        <form
          onSubmit={onSubmit}
          className="w-full max-w-sm space-y-6"
          data-testid="login-form"
        >
          <div>
            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">
              Sign in
            </div>
            <h1 className="font-display font-bold text-3xl tracking-tight">Welcome back</h1>
          </div>

          <div className="space-y-5">
            <div>
              <label className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 w-full bg-transparent border-b border-slate-700 focus:border-[#c8102e] outline-none py-3 text-white"
                data-testid="login-email-input"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                Password
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 w-full bg-transparent border-b border-slate-700 focus:border-[#c8102e] outline-none py-3 text-white"
                data-testid="login-password-input"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full con-ganas-btn rounded-sm h-11"
            data-testid="login-submit-button"
          >
            {loading ? "Entering..." : "Enter the Forge"}
          </Button>

          <div className="text-xs text-slate-500">
            New to the taller?{" "}
            <Link to="/signup" className="text-slate-200 hover:text-white underline underline-offset-4">
              Create an account
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
