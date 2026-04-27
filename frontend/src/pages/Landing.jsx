import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ArrowRight, Wrench, Sparkles, Shield } from "lucide-react";

export default function Landing() {
  return (
    <div className="relative">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-white/5">
        <div className="absolute inset-0 dot-grid opacity-40" />
        <div
          className="absolute -top-40 -right-40 h-[520px] w-[520px] rounded-full blur-[140px]"
          style={{ background: "rgba(200,16,46,0.25)" }}
        />
        <div className="relative max-w-7xl mx-auto px-6 pt-24 pb-28 grid lg:grid-cols-12 gap-10 items-end">
          <div className="lg:col-span-8 rise">
            <div className="text-[11px] uppercase tracking-[0.35em] text-slate-500 mb-6">
              Cyber-Chicano · Creator-Owned · Soulfire
            </div>
            <h1 className="font-display font-bold text-5xl sm:text-6xl lg:text-7xl leading-[0.95] tracking-tighter">
              Forge apps with
              <br />
              <span className="chrome-gradient">chrome-grade</span>
              <br />
              <span className="candy-text">soul.</span>
            </h1>
            <p className="mt-8 max-w-xl text-slate-400 text-lg leading-relaxed">
              El Arquitecto is a vibe coding forge. Type your vision, pick a category, hit
              <span className="text-white font-medium"> Con Ganas</span>. The Cultural Engine
              injects Soulfire Guardrails — 48kHz audio, Emotional Math, Creator Equity DNA —
              before shipping the boilerplate.
            </p>
            <div className="mt-10 flex items-center gap-3">
              <Link to="/signup" data-testid="hero-cta-start">
                <Button size="lg" className="con-ganas-btn rounded-sm h-12 px-7">
                  Start Forging
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
              <Link to="/login" data-testid="hero-cta-signin">
                <Button
                  variant="ghost"
                  size="lg"
                  className="h-12 text-slate-300 hover:text-white hover:bg-white/5 rounded-sm border border-white/10"
                >
                  Sign in
                </Button>
              </Link>
            </div>
          </div>

          <div className="lg:col-span-4">
            <div className="relative bg-[#050505] border border-white/10 rounded-md p-5 font-mono-term text-[12px] shadow-2xl">
              <div className="flex items-center gap-1.5 mb-3">
                <span className="h-2.5 w-2.5 rounded-full bg-[#c8102e]" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
                <span className="ml-2 text-[10px] uppercase tracking-[0.3em] text-slate-500">
                  el-terminal
                </span>
              </div>
              <div className="space-y-1.5 text-slate-400">
                <div>&gt; arquitecto init --soulfire</div>
                <div className="text-slate-300">[planning-agent] Setting the foundation...</div>
                <div className="text-slate-300">
                  [cultural-filter] Injecting guardrails{" "}
                  <span className="text-[#c8102e]">music</span>
                </div>
                <div className="text-slate-300">[frontend-agent] Connecting the wires...</div>
                <div className="text-[#c8102e] term-caret">[forge] Forging the Logic</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value props */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-3 gap-6">
        {[
          {
            icon: Wrench,
            title: "The Cultural Engine",
            body:
              "Every prompt is refined with a Chicano AI Architect preamble and category-specific Soulfire Guardrails before it ever reaches the model.",
          },
          {
            icon: Sparkles,
            title: "Claude Sonnet 4.5 Forge",
            body:
              "Production-grade boilerplates. No placeholder TODOs. Each artifact ships with a SOULFIRE.json manifest for provenance.",
          },
          {
            icon: Shield,
            title: "Creator-Owned Equity",
            body:
              "DNA metadata tagging, transparent royalty splits, and consent-first community primitives baked into the defaults.",
          },
        ].map((f) => (
          <div
            key={f.title}
            className="relative bg-[#121212] border border-white/10 rounded-md p-7 hover:border-white/20 transition-colors"
          >
            <f.icon className="h-5 w-5 text-[#c8102e]" />
            <h3 className="mt-4 font-display font-semibold text-xl tracking-tight">{f.title}</h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">{f.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
