import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API, CATEGORIES } from "../lib/api";
import { Button } from "../components/ui/button";
import { Hammer, Flame, Cpu } from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const [prompt, setPrompt] = useState("");
  const [category, setCategory] = useState("music");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [files, setFiles] = useState([]);
  const logRef = useRef(null);
  const abortRef = useRef(null);
  const nav = useNavigate();

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const pushLog = (line) =>
    setLogs((prev) => [...prev, { id: prev.length, text: line }]);

  const runStream = async () => {
    if (prompt.trim().length < 8) {
      toast.error("Give the forge at least a sentence.");
      return;
    }
    setLoading(true);
    setLogs([]);
    setFiles([]);

    const token = localStorage.getItem("arq_token");
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch(`${API}/artifacts/generate-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ prompt, category }),
        signal: ctrl.signal,
      });

      if (!res.ok || !res.body) {
        const err = await res.text().catch(() => "");
        throw new Error(err || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let artifactId = null;

      // SSE frames are separated by a blank line (\n\n).
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          // Each frame may have multiple `data:` lines — concatenate per spec.
          const dataLines = frame
            .split("\n")
            .filter((l) => l.startsWith("data:"))
            .map((l) => l.slice(5).trim());
          if (dataLines.length === 0) continue;
          let payload;
          try {
            payload = JSON.parse(dataLines.join("\n"));
          } catch {
            continue;
          }
          if (payload.event === "log") {
            pushLog(payload.msg);
          } else if (payload.event === "file") {
            setFiles((prev) => [...prev, payload]);
          } else if (payload.event === "done") {
            artifactId = payload.id;
            pushLog(`[done] artifact ${payload.id.slice(0, 8)}…`);
            // Cultura Vibe completion mural
            const arte = [
              "",
              "  .--------------------------------------------------.",
              "  |  [OK] ARTIFACT FORGED CON GANAS                  |",
              "  '--------------------------------------------------'",
              "                                                      ",
              "    ██████╗██╗   ██╗██╗  ████████╗██╗   ██╗██████╗  █████╗ ",
              "   ██╔════╝██║   ██║██║  ╚══██╔══╝██║   ██║██╔══██╗██╔══██╗",
              "   ██║     ██║   ██║██║     ██║   ██║   ██║██████╔╝███████║",
              "   ██║     ██║   ██║██║     ██║   ██║   ██║██╔══██╗██╔══██║",
              "   ╚██████╗╚██████╔╝███████╗██║   ╚██████╔╝██║  ██║██║  ██║",
              "    ╚═════╝ ╚═════╝ ╚══════╝╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝",
              "",
              "    >> Certified Soulfire DNA — 48kHz Standard <<",
              "",
            ];
            setLogs((prev) => [
              ...prev,
              ...arte.map((text, i) => ({ id: prev.length + i, text })),
            ]);
          } else if (payload.event === "error") {
            pushLog(`[error] ${payload.msg}`);
            toast.error(payload.msg);
          }
        }
      }

      if (artifactId) {
        toast.success("Artifact forged.");
        setTimeout(() => nav(`/artifact/${artifactId}`), 600);
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        pushLog(`[error] ${err.message}`);
        toast.error(err.message || "Forge failed");
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  return (
    <div className="relative max-w-7xl mx-auto px-6 py-14">
      <div className="mb-10 rise">
        <div className="text-[10px] uppercase tracking-[0.35em] text-slate-500 mb-3 flex items-center gap-2">
          <Flame className="h-3 w-3 text-[#c8102e]" />
          El Centro
        </div>
        <h1 className="font-display font-bold text-4xl sm:text-5xl tracking-tighter">
          Describe the vision.
          <br />
          <span className="chrome-gradient">What are we forging today?</span>
        </h1>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* El Centro — input */}
        <div className="lg:col-span-7 space-y-5">
          <div className="el-centro bg-[#0a0a0a] border border-slate-700 rounded-md p-1">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
              rows={10}
              placeholder="A community-owned music app that pays artists per-listen, with 48kHz lossless streaming and DNA-tagged royalty splits…"
              className="w-full bg-transparent text-white placeholder:text-slate-600 outline-none resize-none p-5 text-lg leading-relaxed font-[Manrope]"
              data-testid="el-centro-input"
            />
          </div>

          {/* Category picker */}
          <div>
            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-3">
              Cultural Filter
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {CATEGORIES.map((c) => {
                const active = category === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    disabled={loading}
                    onClick={() => setCategory(c.id)}
                    className={`text-left p-4 rounded-sm border transition-all ${
                      active
                        ? "border-[#c8102e] bg-[#c8102e]/5 candy-glow"
                        : "border-white/10 hover:border-white/30 bg-[#121212]"
                    }`}
                    data-testid={`category-${c.id}`}
                  >
                    <div className="font-display font-semibold text-[15px]">{c.label}</div>
                    <div className="mt-1 text-[11px] text-slate-500 leading-snug">
                      {c.tagline}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button
              onClick={runStream}
              disabled={loading}
              className="con-ganas-btn rounded-sm h-12 px-7 text-sm"
              data-testid="con-ganas-button"
            >
              <Hammer className="h-4 w-4 mr-2" />
              {loading ? "Forging the Logic..." : "Forge Con Ganas"}
            </Button>
            <div className="text-[11px] uppercase tracking-[0.25em] text-slate-600">
              {prompt.length}/4000
            </div>
          </div>
        </div>

        {/* El Terminal */}
        <div className="lg:col-span-5">
          <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-3 flex items-center gap-2">
            <Cpu className="h-3 w-3" />
            El Terminal · Live
          </div>
          <div
            className="relative bg-[#050505] border border-white/10 rounded-md shadow-[inset_0_0_30px_rgba(0,0,0,1)] overflow-hidden"
            data-testid="el-terminal"
          >
            <div className="flex items-center gap-1.5 px-4 py-3 border-b border-white/5 bg-black/50">
              <span className="h-2.5 w-2.5 rounded-full bg-[#c8102e]" />
              <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
              <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
              <span className="ml-3 text-[10px] uppercase tracking-[0.3em] text-slate-500">
                forge.console · sse
              </span>
              <span
                className={`ml-auto text-[10px] uppercase tracking-[0.3em] ${
                  loading ? "text-[#c8102e]" : "text-slate-600"
                }`}
              >
                {loading ? "● live" : "idle"}
              </span>
            </div>
            <div
              ref={logRef}
              className="scanlines p-4 h-[420px] overflow-y-auto font-mono-term text-[12px] leading-relaxed text-slate-300"
            >
              {logs.length === 0 && (
                <div className="text-slate-600">
                  Waiting for input. The agents stand by.
                </div>
              )}
              {logs.map((l, idx) => (
                <div
                  key={l.id}
                  className={`whitespace-pre ${
                    l.text.startsWith("[error]")
                      ? "text-red-400"
                      : l.text.startsWith("[ok]") || l.text.startsWith("[done]")
                      ? "text-emerald-300"
                      : l.text.startsWith("[forge]")
                      ? "text-[#c8102e]"
                      : l.text.startsWith("  .") || l.text.startsWith("  '") || l.text.startsWith("  |")
                      ? "text-[#c8102e]"
                      : l.text.includes("█") || l.text.includes("╔") || l.text.includes("╚")
                      ? "chrome-gradient"
                      : l.text.includes(">> Certified")
                      ? "text-[#c8102e]"
                      : "text-slate-300"
                  }`}
                  data-testid={`term-line-${idx}`}
                >
                  {l.text || "\u00A0"}
                </div>
              ))}
              {loading && <div className="text-[#c8102e] term-caret">&nbsp;</div>}
            </div>
          </div>

          {files.length > 0 && (
            <div className="mt-4">
              <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2 flex items-center justify-between">
                <span>Files Forged</span>
                <span className="text-slate-600">{files.length}</span>
              </div>
              <div className="bg-[#121212] border border-white/10 rounded-md divide-y divide-white/5 max-h-56 overflow-y-auto">
                {files.map((f, i) => (
                  <div
                    key={`${f.path}-${i}`}
                    className="px-3 py-2 flex items-center justify-between text-[12px] font-mono-term"
                    data-testid={`forged-file-${i}`}
                  >
                    <span className="text-slate-200 truncate">{f.path}</span>
                    <span className="text-slate-500 shrink-0 ml-3">{f.lines} ln</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
