import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, API, CATEGORIES } from "../lib/api";
import { Button } from "../components/ui/button";
import { Download, ArrowLeft, File as FileIcon } from "lucide-react";

const catLabel = (id) => CATEGORIES.find((c) => c.id === id)?.label || id;

export default function ArtifactView() {
  const { id } = useParams();
  const [artifact, setArtifact] = useState(null);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get(`/artifacts/${id}`)
      .then((res) => setArtifact(res.data))
      .finally(() => setLoading(false));
  }, [id]);

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
    </div>
  );
}
