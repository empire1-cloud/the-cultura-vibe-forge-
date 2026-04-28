import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, API } from "../lib/api";
import { Button } from "../components/ui/button";
import { Check, Trash2, Inbox, ShieldAlert, ExternalLink, Hash, Image as ImageIcon, Volume2, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const PLATFORM_META = {
  x: { label: "X", color: "text-slate-100", chip: "bg-slate-100/10 border-slate-100/20" },
  instagram: {
    label: "Instagram",
    color: "text-pink-300",
    chip: "bg-pink-500/10 border-pink-500/20",
  },
  tiktok: {
    label: "TikTok",
    color: "text-emerald-200",
    chip: "bg-emerald-500/10 border-emerald-500/20",
  },
  linkedin: {
    label: "LinkedIn",
    color: "text-sky-200",
    chip: "bg-sky-500/10 border-sky-500/20",
  },
};

const STATUS_BADGE = {
  drafted: "border-slate-600 text-slate-300",
  needs_review: "border-amber-500/50 text-amber-300 bg-amber-500/10",
  approved: "border-emerald-500/50 text-emerald-200 bg-emerald-500/10",
};

export default function Drafts() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [regenning, setRegenning] = useState({});
  const [imgVer, setImgVer] = useState({});
  const pollRef = useRef(null);

  const refresh = () =>
    api.get("/drafts").then((r) => {
      setItems(r.data);
      setLoading(false);
    });

  useEffect(() => {
    refresh();
    return () => clearTimeout(pollRef.current);
  }, []);

  // Poll while any draft is still rendering its mockup
  useEffect(() => {
    clearTimeout(pollRef.current);
    const pending = items.some((d) => !d.mockup_ready);
    if (pending) {
      pollRef.current = setTimeout(refresh, 4000);
    }
    return () => clearTimeout(pollRef.current);
  }, [items]);

  const approve = async (id) => {
    try {
      await api.post(`/drafts/${id}/approve`);
      toast.success("Draft approved");
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Approve failed");
    }
  };

  const discard = async (id) => {
    try {
      await api.delete(`/drafts/${id}`);
      toast.success("Discarded");
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    }
  };

  const regenerate = async (id) => {
    setRegenning((p) => ({ ...p, [id]: true }));
    try {
      await api.post(`/drafts/${id}/mockup/regenerate`);
      // Optimistically flip the local state so the spinner shows immediately.
      setItems((prev) =>
        prev.map((d) =>
          d.id === id ? { ...d, mockup_ready: false, mockup_failed: false } : d,
        ),
      );
      // Bump cache-bust version so next load pulls a fresh PNG.
      setImgVer((p) => ({ ...p, [id]: (p[id] || 0) + 1 }));
      toast.success("Re-rendering mockup…");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Regen failed");
    } finally {
      setRegenning((p) => ({ ...p, [id]: false }));
    }
  };

  const filtered = items.filter((d) => filter === "all" || d.status === filter);

  return (
    <div className="max-w-6xl mx-auto px-6 py-14">
      <div className="mb-10 rise">
        <div className="text-[10px] uppercase tracking-[0.35em] text-slate-500 mb-3 flex items-center gap-2">
          <Inbox className="h-3 w-3 text-[#c8102e]" />
          Amplifier · Drafts
        </div>
        <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tighter">
          The Hustle.
          <br />
          <span className="candy-text">Drafted, not posted.</span>
        </h1>
        <p className="mt-3 text-slate-400 max-w-xl">
          Every draft passes the Soulfire Filter. Approve before it ships. No autopost — yet.
        </p>
      </div>

      <div className="flex items-center gap-2 mb-6">
        {[
          { id: "all", label: "All" },
          { id: "drafted", label: "Drafted" },
          { id: "needs_review", label: "Needs Review" },
          { id: "approved", label: "Approved" },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-sm text-[10px] uppercase tracking-[0.25em] font-bold border transition-all ${
              filter === f.id
                ? "border-[#c8102e]/60 text-white bg-[#c8102e]/10"
                : "border-white/10 text-slate-400 hover:border-white/30"
            }`}
            data-testid={`drafts-filter-${f.id}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-slate-500 text-sm">Loading drafts...</div>
      ) : filtered.length === 0 ? (
        <div className="border border-dashed border-white/10 rounded-md p-16 text-center">
          <Inbox className="h-10 w-10 mx-auto text-slate-600" />
          <div className="mt-4 text-slate-400">No drafts yet. Hit "Amplify" on any artifact.</div>
          <Link to="/taller" className="inline-block mt-6">
            <Button className="con-ganas-btn rounded-sm">Open The Taller</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((d) => {
            const meta = PLATFORM_META[d.platform] || PLATFORM_META.x;
            return (
              <div
                key={d.id}
                className={`bg-[#121212] border border-white/10 rounded-md p-6 ${
                  d.universe === "nothing" ? "font-mono-term" : ""
                }`}
                data-testid={`draft-${d.id}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] uppercase tracking-[0.25em] font-bold px-2 py-0.5 border rounded-sm ${meta.chip} ${meta.color}`}
                    >
                      {meta.label}
                    </span>
                    <span className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                      {d.universe === "nothing" ? "· Nothing Protocol" : "· Cultura Vibe"}
                    </span>
                    <span
                      className={`text-[10px] uppercase tracking-[0.22em] px-2 py-0.5 border rounded-sm ${
                        STATUS_BADGE[d.status] || STATUS_BADGE.drafted
                      }`}
                      data-testid={`draft-status-${d.id}`}
                    >
                      {d.status.replace("_", " ")}
                    </span>
                  </div>
                  <Link
                    to={`/artifact/${d.artifact_id}`}
                    className="text-[10px] uppercase tracking-[0.25em] text-slate-500 hover:text-slate-200 inline-flex items-center gap-1"
                  >
                    <ExternalLink className="h-3 w-3" /> {d.artifact_title}
                  </Link>
                </div>

                <div className="grid lg:grid-cols-5 gap-5">
                  <div className="lg:col-span-2">
                    {/* Rendered mockup */}
                    <div className="aspect-[16/10] relative bg-[#050505] border border-white/10 rounded-sm overflow-hidden group">
                      {d.mockup_ready && !d.mockup_failed ? (
                        <img
                          src={`${API}/drafts/${d.id}/mockup.png?token=${encodeURIComponent(
                            localStorage.getItem("arq_token") || "",
                          )}&v=${imgVer[d.id] || 0}`}
                          alt={d.alt_text || d.mockup_brief}
                          className="w-full h-full object-cover"
                          data-testid={`draft-mockup-img-${d.id}`}
                        />
                      ) : d.mockup_failed ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 text-[11px]">
                          <ImageIcon className="h-5 w-5 mb-2" />
                          Mockup render unavailable
                        </div>
                      ) : (
                        <div
                          className="absolute inset-0 flex flex-col items-center justify-center text-slate-400 text-[11px] uppercase tracking-[0.25em]"
                          data-testid={`draft-mockup-loading-${d.id}`}
                        >
                          <Loader2 className="h-5 w-5 mb-2 text-[#c8102e] animate-spin" />
                          Rendering · Nano Banana
                        </div>
                      )}
                      {d.mockup_brief && (
                        <button
                          onClick={() => regenerate(d.id)}
                          disabled={!!regenning[d.id] || !d.mockup_ready}
                          className="absolute top-2 right-2 p-1.5 rounded-sm bg-black/70 hover:bg-[#c8102e]/30 border border-white/10 hover:border-[#c8102e]/60 text-slate-300 hover:text-white transition-all opacity-0 group-hover:opacity-100 disabled:opacity-40 disabled:cursor-not-allowed"
                          title="Regenerate mockup"
                          data-testid={`draft-regen-${d.id}`}
                        >
                          <RefreshCw
                            className={`h-3.5 w-3.5 ${regenning[d.id] ? "animate-spin" : ""}`}
                          />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="lg:col-span-3 space-y-3">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">
                        Caption
                      </div>
                      <p
                        className={`whitespace-pre-wrap text-sm leading-relaxed ${
                          d.universe === "nothing" ? "tracking-wide text-slate-200" : "text-slate-100"
                        }`}
                        data-testid={`draft-caption-${d.id}`}
                      >
                        {d.caption}
                      </p>
                    </div>
                    {d.hashtags?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {d.hashtags.map((h) => (
                          <span
                            key={h}
                            className="text-[11px] text-slate-400 inline-flex items-center"
                          >
                            <Hash className="h-2.5 w-2.5" />
                            {h.replace(/^#/, "")}
                          </span>
                        ))}
                      </div>
                    )}
                    {d.mockup_brief && (
                      <div className="pt-2">
                        <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1 inline-flex items-center gap-1">
                          <ImageIcon className="h-3 w-3" /> Mockup Brief
                        </div>
                        <p className="text-[12px] text-slate-400 leading-relaxed">{d.mockup_brief}</p>
                      </div>
                    )}
                    {d.audio_brief && (
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.3em] text-[#c8102e] mb-1 inline-flex items-center gap-1">
                          <Volume2 className="h-3 w-3" /> 48kHz · Audio Brief
                        </div>
                        <p className="text-[12px] text-slate-400 leading-relaxed">{d.audio_brief}</p>
                      </div>
                    )}
                  </div>
                </div>

                {d.soulfire_flags?.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-white/5 flex items-start gap-2 text-[11px] text-amber-300">
                    <ShieldAlert className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    <div>
                      <span className="uppercase tracking-[0.25em] text-[10px] font-bold">
                        Soulfire flags:
                      </span>{" "}
                      {d.soulfire_flags.join(" · ")}
                    </div>
                  </div>
                )}

                <div className="mt-5 flex items-center justify-end gap-2">
                  <button
                    onClick={() => discard(d.id)}
                    className="px-3 py-2 text-[10px] uppercase tracking-[0.25em] font-bold border border-white/10 text-slate-400 hover:border-red-500/40 hover:text-red-300 rounded-sm transition-all inline-flex items-center gap-1.5"
                    data-testid={`draft-discard-${d.id}`}
                  >
                    <Trash2 className="h-3 w-3" /> Discard
                  </button>
                  {d.status !== "approved" && (
                    <button
                      onClick={() => approve(d.id)}
                      className="px-3 py-2 text-[10px] uppercase tracking-[0.25em] font-bold con-ganas-btn rounded-sm inline-flex items-center gap-1.5"
                      data-testid={`draft-approve-${d.id}`}
                    >
                      <Check className="h-3 w-3" /> Approve
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
