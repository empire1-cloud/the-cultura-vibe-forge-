import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, API, CATEGORIES } from "../lib/api";
import { Button } from "../components/ui/button";
import { Download, ArrowLeft, File as FileIcon, Megaphone, X as XIcon } from "lucide-react";
import { toast } from "sonner";

const catLabel = (id) => CATEGORIES.find((c) => c.id === id)?.label || id;

const PLATFORMS = [
  { id: "x", label: "X" },
  { id: "instagram", label: "Instagram" },
  { id: "tiktok", label: "TikTok" },
  { id: "linkedin", label: "LinkedIn" },
];

export default function ArtifactView() {
  const { id } = useParams();
  const nav = useNavigate();
  const [artifact, setArtifact] = useState(null);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showAmplify, setShowAmplify] = useState(false);
  const [universe, setUniverse] = useState("cultura");
  const [picked, setPicked] = useState(["x", "instagram"]);
  const [amplifying, setAmplifying] = useState(false);

  useEffect(() => {
    api
      .get(`/artifacts/${id}`)
      .then((res) => setArtifact(res.data))
      .finally(() => setLoading(false));
  }, [id]);

  const togglePlatform = (pid) =>
    setPicked((prev) =>
      prev.includes(pid) ? prev.filter((p) => p !== pid) : [...prev, pid],
    );

  const runAmplify = async () => {
    if (picked.length === 0) {
      toast.error("Pick at least one platform.");
      return;
    }
    setAmplifying(true);
    try {
      const res = await api.post("/drafts/generate", {
        artifact_id: id,
        platforms: picked,
        universe,
      });
      toast.success(`${res.data.drafts.length} drafts forged.`);
      setShowAmplify(false);
      nav("/drafts");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Amplifier failed");
    } finally {
      setAmplifying(false);
    }
  };

  const downloadZip = () => {
    const token = localStorage.getItem("arq_token");
    const url = `${API}/artifacts/${id}/download?token=${encodeURIComponent(token || "")}`;
    window.location.href = url;
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-16 text-slate-500 text-sm">
        Loading artifact...
      </div>
    );
  }
  if (!artifact) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-16 text-slate-400">
        Artifact not found.
      </div>
    );
  }

  const file = artifact.files[active];

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <Link
        to="/taller"
        className="inline-flex items-center text-[11px] uppercase tracking-[0.3em] text-slate-500 hover:text-slate-200 mb-8"
        data-testid="back-to-taller"
      >
        <ArrowLeft className="h-3.5 w-3.5 mr-2" />
        The Taller
      </Link>

      <div className="flex items-start justify-between gap-6 mb-10">
        <div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">
            {catLabel(artifact.category)} · {artifact.files.length} files
          </div>
          <h1 className="font-display font-bold text-4xl tracking-tighter" data-testid="artifact-title">
            {artifact.title}
          </h1>
          <p className="mt-3 text-slate-400 max-w-2xl leading-relaxed">
            {artifact.description}
          </p>
        </div>
        <Button
          onClick={downloadZip}
          className="con-ganas-btn rounded-sm h-11 px-5 shrink-0"
          data-testid="download-zip-button"
        >
          <Download className="h-4 w-4 mr-2" />
          Download .zip
        </Button>
      </div>

      <div className="-mt-6 mb-8 flex items-center gap-2">
        <button
          onClick={() => setShowAmplify(true)}
          className="px-4 py-2 text-[10px] uppercase tracking-[0.25em] font-bold border border-[#c8102e]/40 bg-[#c8102e]/10 text-[#ff5b6f] hover:bg-[#c8102e]/20 rounded-sm inline-flex items-center gap-1.5 transition-all"
          data-testid="amplify-button"
        >
          <Megaphone className="h-3 w-3" /> Amplify
        </button>
        <span className="text-[10px] uppercase tracking-[0.25em] text-slate-600">
          Send to the Amplifier · drafts only
        </span>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* File tree */}
        <aside className="lg:col-span-3">
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-3">
            Files
          </div>
          <div className="bg-[#121212] border border-white/10 rounded-md divide-y divide-white/5 overflow-hidden">
            {artifact.files.map((f, idx) => (
              <button
                key={f.path}
                onClick={() => setActive(idx)}
                className={`w-full text-left px-4 py-3 flex items-center gap-2 text-sm transition-colors ${
                  idx === active ? "bg-[#c8102e]/10 text-white" : "text-slate-400 hover:text-white hover:bg-white/5"
                }`}
                data-testid={`file-tab-${idx}`}
              >
                <FileIcon className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate font-mono-term text-[12px]">{f.path}</span>
              </button>
            ))}
          </div>

          {/* Terminal log */}
          <div className="mt-6">
            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-3">
              Forge Log
            </div>
            <div className="bg-[#050505] border border-white/10 rounded-md p-3 font-mono-term text-[11px] text-slate-400 space-y-1 max-h-56 overflow-y-auto">
              {artifact.terminal_log.map((l, i) => (
                <div key={i} className={l.startsWith("[ok]") ? "text-emerald-300" : l.startsWith("[forge]") ? "text-[#c8102e]" : ""}>
                  {l}
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Code viewer */}
        <section className="lg:col-span-9">
          <div className="bg-[#050505] border border-white/10 rounded-md overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-black/50">
              <div className="font-mono-term text-[12px] text-slate-300">{file.path}</div>
              <div className="text-[10px] uppercase tracking-[0.3em] text-slate-600">
                {file.content.split("\n").length} lines
              </div>
            </div>
            <pre
              className="p-5 overflow-x-auto text-[12.5px] leading-relaxed font-mono-term text-slate-200 max-h-[640px] overflow-y-auto"
              data-testid="file-content"
            >
              <code>{file.content}</code>
            </pre>
          </div>

          <details className="mt-6 bg-[#121212] border border-white/10 rounded-md p-5">
            <summary className="cursor-pointer text-[11px] uppercase tracking-[0.3em] text-slate-500 hover:text-slate-200">
              View Refined Prompt (Soulfire)
            </summary>
            <pre className="mt-4 whitespace-pre-wrap text-[12.5px] text-slate-300 font-mono-term">
              {artifact.refined_prompt}
            </pre>
          </details>
        </section>
      </div>

      {showAmplify && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={() => !amplifying && setShowAmplify(false)}
          data-testid="amplify-modal"
        >
          <div
            className="bg-[#0a0a0a] border border-white/10 rounded-md max-w-lg w-full p-7 candy-glow"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-5">
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-[#c8102e] mb-1.5">
                  Amplifier
                </div>
                <h3 className="font-display font-bold text-2xl tracking-tight">
                  Draft the hustle.
                </h3>
              </div>
              <button
                onClick={() => setShowAmplify(false)}
                disabled={amplifying}
                className="text-slate-500 hover:text-white"
              >
                <XIcon className="h-4 w-4" />
              </button>
            </div>

            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">
              Universe
            </div>
            <div className="grid grid-cols-2 gap-2 mb-5">
              {[
                { id: "cultura", label: "Cultura Vibe", sub: "Sleek · Chrome · Candy" },
                { id: "nothing", label: "Nothing Protocol", sub: "Dot-matrix · Transparent" },
              ].map((u) => (
                <button
                  key={u.id}
                  onClick={() => setUniverse(u.id)}
                  disabled={amplifying}
                  className={`text-left p-3 rounded-sm border transition-all ${
                    universe === u.id
                      ? "border-[#c8102e]/60 bg-[#c8102e]/10"
                      : "border-white/10 hover:border-white/30"
                  } ${u.id === "nothing" ? "font-mono-term" : ""}`}
                  data-testid={`universe-${u.id}`}
                >
                  <div className="font-display font-semibold text-sm">{u.label}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{u.sub}</div>
                </button>
              ))}
            </div>

            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">
              Platforms
            </div>
            <div className="grid grid-cols-2 gap-2 mb-6">
              {PLATFORMS.map((p) => {
                const on = picked.includes(p.id);
                return (
                  <button
                    key={p.id}
                    onClick={() => togglePlatform(p.id)}
                    disabled={amplifying}
                    className={`text-left p-3 rounded-sm border transition-all ${
                      on
                        ? "border-[#c8102e]/60 bg-[#c8102e]/10 text-white"
                        : "border-white/10 text-slate-400 hover:border-white/30"
                    }`}
                    data-testid={`platform-${p.id}`}
                  >
                    <div className="font-display font-medium text-sm">{p.label}</div>
                  </button>
                );
              })}
            </div>

            <Button
              onClick={runAmplify}
              disabled={amplifying || picked.length === 0}
              className="w-full con-ganas-btn rounded-sm h-11"
              data-testid="amplify-submit"
            >
              <Megaphone className="h-4 w-4 mr-2" />
              {amplifying ? "Drafting…" : `Draft ${picked.length} ${picked.length === 1 ? "post" : "posts"}`}
            </Button>
            <div className="mt-3 text-[10px] uppercase tracking-[0.25em] text-slate-600 text-center">
              Drafts only · nothing is posted
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
