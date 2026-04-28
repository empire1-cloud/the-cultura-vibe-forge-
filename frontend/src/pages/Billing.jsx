import { useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Crown, Check, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

const POLL_INTERVAL_MS = 2200;
const POLL_MAX = 30;

export default function Billing() {
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [pkgs, setPkgs] = useState([]);
  const [creating, setCreating] = useState(false);
  const [polling, setPolling] = useState(false);
  const [pollState, setPollState] = useState(null);
  const pollTimer = useRef(null);

  const fetchAll = () => {
    Promise.all([api.get("/billing/me"), api.get("/billing/packages")]).then(([m, p]) => {
      setMe(m.data);
      setPkgs(p.data);
    });
  };

  useEffect(() => {
    fetchAll();
    return () => clearTimeout(pollTimer.current);
  }, []);

  const sessionId = params.get("session_id");
  const canceled = params.get("canceled");

  useEffect(() => {
    if (!sessionId) return;
    setPolling(true);
    let attempts = 0;

    const poll = async () => {
      attempts += 1;
      try {
        const res = await api.get(`/billing/checkout/status/${sessionId}`);
        setPollState(res.data);
        if (res.data.payment_status === "paid") {
          setPolling(false);
          toast.success("Maestro Pass activated.");
          fetchAll();
          return;
        }
        if (res.data.status === "expired" || attempts >= POLL_MAX) {
          setPolling(false);
          toast.error("Payment session expired or timed out.");
          return;
        }
        pollTimer.current = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        setPolling(false);
        toast.error(err?.response?.data?.detail || "Status check failed");
      }
    };
    poll();
    return () => clearTimeout(pollTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (canceled) {
      toast("Payment canceled.", { description: "No charge was made." });
    }
  }, [canceled]);

  const upgrade = async (packageId) => {
    setCreating(true);
    try {
      const res = await api.post("/billing/checkout", {
        package_id: packageId,
        origin_url: window.location.origin,
      });
      window.location.href = res.data.url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Checkout failed");
      setCreating(false);
    }
  };

  const isMaestro = me?.tier === "maestro";

  return (
    <div className="max-w-5xl mx-auto px-6 py-14">
      <div className="mb-12 rise">
        <div className="text-[10px] uppercase tracking-[0.35em] text-slate-500 mb-3 flex items-center gap-2">
          <Crown className="h-3 w-3 text-[#c8102e]" />
          Billing
        </div>
        <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tighter">
          Forge harder.
          <br />
          <span className="candy-text">Forge longer.</span>
        </h1>
        <p className="mt-4 text-slate-400 max-w-xl">
          Aprendiz keeps the lights on. Maestro lets you push the forge — 200/hr, 5 concurrent,
          priority queue. One pass. Thirty days. Owned.
        </p>
      </div>

      {/* Current tier card */}
      <div
        className="mb-8 bg-[#121212] border border-white/10 rounded-md p-6 flex items-center justify-between"
        data-testid="current-tier-card"
      >
        <div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Current tier</div>
          <div className="mt-2 flex items-baseline gap-3">
            <span
              className={`font-display font-bold text-2xl tracking-tight ${
                isMaestro ? "candy-text" : "text-slate-200"
              }`}
              data-testid="current-tier-label"
            >
              {isMaestro ? "Maestro" : "Aprendiz"}
            </span>
            {me?.tier_until && (
              <span className="text-xs text-slate-500">
                until {new Date(me.tier_until).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        {me && (
          <div className="text-right text-[11px] text-slate-500 leading-relaxed">
            <div>{me.limits.hour}/hr · {me.limits.day}/day</div>
            <div>{me.limits.concurrent} concurrent</div>
          </div>
        )}
      </div>

      {/* Polling banner */}
      {polling && (
        <div
          className="mb-8 border border-[#c8102e]/40 bg-[#c8102e]/5 rounded-md p-5 flex items-center gap-3"
          data-testid="polling-banner"
        >
          <Loader2 className="h-4 w-4 text-[#c8102e] animate-spin" />
          <div>
            <div className="text-sm font-medium">Confirming payment with Stripe…</div>
            <div className="text-xs text-slate-500">This usually takes a few seconds.</div>
          </div>
        </div>
      )}

      {pollState?.payment_status === "paid" && !polling && (
        <div className="mb-8 border border-emerald-500/30 bg-emerald-500/5 rounded-md p-5">
          <div className="font-display font-semibold text-emerald-300">Maestro activated</div>
          <div className="text-xs text-slate-400 mt-1">
            Welcome to the boulevard. Your forge is unlocked.
          </div>
        </div>
      )}

      {/* Pricing grid */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Aprendiz card */}
        <div className="bg-[#121212] border border-white/10 rounded-md p-7 flex flex-col">
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Free</div>
          <h3 className="mt-2 font-display font-bold text-2xl tracking-tight">Aprendiz</h3>
          <div className="mt-3 text-3xl font-display font-black tracking-tighter">
            $0<span className="text-base text-slate-500 font-medium"> / forever</span>
          </div>
          <ul className="mt-6 space-y-2 text-sm text-slate-300">
            {[
              "20 forges per hour",
              "50 forges per day",
              "2 concurrent",
              "Full zip download + SOULFIRE.json",
            ].map((f) => (
              <li key={f} className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-slate-500" />
                {f}
              </li>
            ))}
          </ul>
          <div className="mt-auto pt-6 text-[11px] uppercase tracking-[0.25em] text-slate-600">
            {!isMaestro ? "● Active" : "Downgraded after Maestro expires"}
          </div>
        </div>

        {/* Maestro card */}
        {pkgs.map((p) => (
          <div
            key={p.id}
            className="relative bg-[#0d0d0d] border border-[#c8102e]/40 rounded-md p-7 flex flex-col candy-glow overflow-hidden"
            data-testid={`pkg-${p.id}`}
          >
            <div
              className="absolute -top-12 -right-12 h-40 w-40 rounded-full blur-3xl"
              style={{ background: "rgba(200,16,46,0.25)" }}
            />
            <div className="relative">
              <div className="text-[10px] uppercase tracking-[0.3em] text-[#c8102e] flex items-center gap-2">
                <Crown className="h-3 w-3" /> Recommended
              </div>
              <h3 className="mt-2 font-display font-bold text-2xl tracking-tight">{p.label}</h3>
              <div className="mt-3 text-3xl font-display font-black tracking-tighter">
                ${p.amount.toFixed(0)}
                <span className="text-base text-slate-500 font-medium"> / {p.duration_days} days</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">{p.tagline}</p>
              <ul className="mt-6 space-y-2 text-sm text-slate-200">
                {[
                  "200 forges per hour",
                  "Effectively unlimited daily",
                  "5 concurrent forges",
                  "Priority queue · early access to new categories",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-[#c8102e]" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                onClick={() => upgrade(p.id)}
                disabled={creating || isMaestro}
                className="con-ganas-btn rounded-sm h-12 w-full mt-7"
                data-testid={`upgrade-${p.id}-button`}
              >
                {isMaestro ? "Already Maestro" : creating ? "Opening Stripe…" : "Upgrade · Pay with Card"}
                {!isMaestro && !creating && <ArrowRight className="h-4 w-4 ml-2" />}
              </Button>
              <div className="mt-3 text-[10px] uppercase tracking-[0.25em] text-slate-600 text-center">
                Stripe-hosted checkout · Test mode
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={() => {
          setParams({});
          nav("/dashboard");
        }}
        className="mt-10 text-[11px] uppercase tracking-[0.3em] text-slate-500 hover:text-slate-200"
      >
        ← Back to El Centro
      </button>
    </div>
  );
}
