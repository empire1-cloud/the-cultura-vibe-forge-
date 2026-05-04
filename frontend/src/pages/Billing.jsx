import { useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Crown, Check, ArrowRight, Loader2, Coins } from "lucide-react";
import { toast } from "sonner";

const POLL_INTERVAL_MS = 2200;
const POLL_MAX = 30;

const TIER_FEATURES = {
  soulfire: [
    "10 forges included / month",
    "Then $10 per overage forge",
    "20 forges/hr · 60/day",
    "3 concurrent forges",
    "Priority queue access",
  ],
  maestro: [
    "50 forges included / month",
    "Then $7 per overage forge",
    "60 forges/hr · 200/day",
    "5 concurrent forges",
    "Priority + early-access categories",
  ],
};

export default function Billing() {
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [usage, setUsage] = useState(null);
  const [pkgs, setPkgs] = useState([]);
  const [liveMode, setLiveMode] = useState(false);
  const [creating, setCreating] = useState(null);
  const [polling, setPolling] = useState(false);
  const [pollState, setPollState] = useState(null);
  const pollTimer = useRef(null);

  const fetchAll = () => {
    Promise.all([
      api.get("/billing/me"),
      api.get("/billing/packages"),
      api.get("/billing/usage"),
    ]).then(([m, p, u]) => {
      setMe(m.data);
      setPkgs(p.data.packages || []);
      setLiveMode(!!p.data.live_mode);
      setUsage(u.data);
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
          toast.success("Payment confirmed.");
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
    if (canceled) toast("Payment canceled.", { description: "No charge was made." });
  }, [canceled]);

  const checkout = async (packageId) => {
    setCreating(packageId);
    try {
      const res = await api.post("/billing/checkout", {
        package_id: packageId,
        origin_url: window.location.origin,
      });
      window.location.href = res.data.url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Checkout failed");
      setCreating(null);
    }
  };

  const tierPackages = pkgs.filter((p) => !p.tier_required);
  const creditPackages = pkgs.filter((p) => p.tier_required);
  const creditPackForCurrent = creditPackages.find((p) => p.tier_required === me?.tier);

  return (
    <div className="max-w-6xl mx-auto px-6 py-14">
      <div className="mb-12 rise">
        <div className="text-[10px] uppercase tracking-[0.35em] text-slate-500 mb-3 flex items-center gap-2">
          <Crown className="h-3 w-3 text-[#c8102e]" />
          Billing
        </div>
        <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tighter">
          Build it. Run it. Ship it.
          <br />
          <span className="candy-text">No terminal required.</span>
        </h1>
        <p className="mt-4 text-slate-400 max-w-xl">
          Flat-fee + overage. Included forges roll over nothing. Predictable on the floor,
          honest at the ceiling.
        </p>
      </div>

      {/* Current tier + cycle usage */}
      <div
        className="mb-8 bg-[#121212] border border-white/10 rounded-md p-6 grid sm:grid-cols-3 gap-6"
        data-testid="current-tier-card"
      >
        <div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Current tier</div>
          <div
            className={`mt-2 font-display font-bold text-2xl tracking-tight ${
              me?.tier?.startsWith("maestro") ? "candy-text" : "text-slate-200"
            }`}
            data-testid="current-tier-label"
          >
            {me?.tier === "maestro"
              ? "Maestro"
              : me?.tier === "soulfire" || me?.tier === "maestro"
              ? "Soulfire"
              : "Aprendiz"}
          </div>
          {me?.tier_until && (
            <div className="text-xs text-slate-500 mt-1">
              renews {new Date(me.tier_until).toLocaleDateString()}
            </div>
          )}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Cycle</div>
          <div className="mt-2 font-display font-bold text-2xl tracking-tight">
            {usage?.cycle?.used ?? 0}
            <span className="text-base text-slate-500"> / {usage?.cycle?.included ?? 0}</span>
          </div>
          <div className="text-xs text-slate-500 mt-1">forges included used</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 inline-flex items-center gap-1">
            <Coins className="h-3 w-3" /> Credits
          </div>
          <div className="mt-2 font-display font-bold text-2xl tracking-tight">
            {me?.forge_credits ?? 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">overage forges available</div>
        </div>
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
          <div className="font-display font-semibold text-emerald-300">Payment confirmed</div>
          <div className="text-xs text-slate-400 mt-1">Account updated. Forge on.</div>
        </div>
      )}

      {/* Tier grid */}
      <div className="grid md:grid-cols-3 gap-4">
        {/* Aprendiz */}
        <div className="bg-[#121212] border border-white/10 rounded-md p-7 flex flex-col">
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Free</div>
          <h3 className="mt-2 font-display font-bold text-2xl tracking-tight">Aprendiz</h3>
          <div className="mt-3 text-3xl font-display font-black tracking-tighter">
            $0<span className="text-base text-slate-500 font-medium"> / forever</span>
          </div>
          <ul className="mt-6 space-y-2 text-sm text-slate-300">
            {[
              "5 forges per hour",
              "10 forges per day",
              "1 concurrent forge",
              "Full zip download + SOULFIRE.json",
            ].map((f) => (
              <li key={f} className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-slate-500" /> {f}
              </li>
            ))}
          </ul>
        </div>

        {tierPackages.map((p) => {
          const isCurrent = me?.tier === p.tier;
          const recommended = p.tier === "maestro";
          return (
            <div
              key={p.id}
              className={`relative bg-[#0d0d0d] rounded-md p-7 flex flex-col border overflow-hidden ${
                recommended
                  ? "border-[#c8102e]/50 candy-glow"
                  : "border-white/10 hover:border-white/30 transition-all"
              }`}
              data-testid={`pkg-${p.id}`}
            >
              {recommended && (
                <div
                  className="absolute -top-12 -right-12 h-40 w-40 rounded-full blur-3xl"
                  style={{ background: "rgba(200,16,46,0.25)" }}
                />
              )}
              <div className="relative">
                <div
                  className={`text-[10px] uppercase tracking-[0.3em] flex items-center gap-2 ${
                    recommended ? "text-[#c8102e]" : "text-slate-500"
                  }`}
                >
                  <Crown className="h-3 w-3" /> {recommended ? "Recommended" : "Subscription"}
                </div>
                <h3 className="mt-2 font-display font-bold text-2xl tracking-tight">{p.label}</h3>
                <div className="mt-3 text-3xl font-display font-black tracking-tighter">
                  ${p.amount.toFixed(0)}
                  <span className="text-base text-slate-500 font-medium"> / month</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{p.tagline}</p>
                <ul className="mt-6 space-y-2 text-sm text-slate-200">
                  {(TIER_FEATURES[p.tier] || []).map((f) => (
                    <li key={f} className="flex items-center gap-2">
                      <Check className="h-3.5 w-3.5 text-[#c8102e]" /> {f}
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={() => checkout(p.id)}
                  disabled={!!creating || isCurrent}
                  className="con-ganas-btn rounded-sm h-12 w-full mt-7"
                  data-testid={`upgrade-${p.id}-button`}
                >
                  {isCurrent
                    ? "Current plan"
                    : creating === p.id
                    ? "Opening Stripe…"
                    : `Upgrade · ${p.label}`}
                  {!isCurrent && creating !== p.id && <ArrowRight className="h-4 w-4 ml-2" />}
                </Button>
                {!liveMode && (
                  <div className="mt-3 text-[10px] uppercase tracking-[0.25em] text-slate-600 text-center">
                    Stripe-hosted checkout · Test Mode
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Credit packs (only for paid tier holders) */}
      {creditPackForCurrent && (
        <div className="mt-12">
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-3 flex items-center gap-2">
            <Coins className="h-3 w-3 text-[#c8102e]" /> Overage Credits
          </div>
          <div
            className="bg-[#121212] border border-white/10 rounded-md p-6 flex items-center justify-between"
            data-testid="credit-pack-card"
          >
            <div>
              <div className="font-display font-semibold text-lg">
                {creditPackForCurrent.label}
              </div>
              <div className="text-sm text-slate-400 mt-1">{creditPackForCurrent.tagline}</div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-2xl font-display font-bold">
                ${creditPackForCurrent.amount.toFixed(2)}
              </div>
              <Button
                onClick={() => checkout(creditPackForCurrent.id)}
                disabled={!!creating}
                className="con-ganas-btn rounded-sm h-11 px-5"
                data-testid={`buy-credit-${creditPackForCurrent.id}`}
              >
                {creating === creditPackForCurrent.id ? "Opening…" : "Buy 1 credit"}
              </Button>
            </div>
          </div>
        </div>
      )}

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
