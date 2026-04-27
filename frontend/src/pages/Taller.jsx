import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, CATEGORIES } from "../lib/api";
import { Button } from "../components/ui/button";
import { Hammer, Folder } from "lucide-react";

const catLabel = (id) => CATEGORIES.find((c) => c.id === id)?.label || id;

export default function Taller() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/artifacts")
      .then((res) => setItems(res.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-14">
      <div className="flex items-end justify-between mb-10">
        <div>
          <div className="text-[10px] uppercase tracking-[0.35em] text-slate-500 mb-3">
            The Taller
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl tracking-tighter">
            Digital <span className="candy-text">Artifacts.</span>
          </h1>
          <p className="mt-3 text-slate-400 max-w-lg">
            Every boilerplate forged in The Taller carries its Soulfire DNA. Download the zip,
            ship it, own it.
          </p>
        </div>
        <Link to="/dashboard">
          <Button className="con-ganas-btn rounded-sm h-11 px-5" data-testid="taller-new-button">
            <Hammer className="h-4 w-4 mr-2" />
            New Forge
          </Button>
        </Link>
      </div>

      {loading ? (
        <div className="text-slate-500 text-sm">Loading the taller...</div>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-white/10 rounded-md p-16 text-center">
          <Folder className="h-10 w-10 mx-auto text-slate-600" />
          <div className="mt-4 text-slate-400">The taller is empty. Nothing forged yet.</div>
          <Link to="/dashboard" className="inline-block mt-6">
            <Button className="con-ganas-btn rounded-sm">Forge your first artifact</Button>
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((a) => (
            <Link
              key={a.id}
              to={`/artifact/${a.id}`}
              className="group relative bg-[#121212] border border-white/10 hover:border-[#c8102e]/60 transition-all rounded-md p-6 overflow-hidden"
              data-testid={`taller-item-${a.id}`}
            >
              <div className="absolute -top-16 -right-16 h-32 w-32 rounded-full blur-3xl bg-[#c8102e]/0 group-hover:bg-[#c8102e]/15 transition-all" />
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                  {catLabel(a.category)}
                </span>
                <span className="text-[10px] uppercase tracking-[0.2em] text-slate-600">
                  {a.file_count} files
                </span>
              </div>
              <h3 className="mt-4 font-display font-semibold text-xl tracking-tight group-hover:text-white">
                {a.title}
              </h3>
              <p className="mt-2 text-sm text-slate-400 line-clamp-3 leading-relaxed">
                {a.description}
              </p>
              <div className="mt-6 text-[10px] uppercase tracking-[0.3em] text-slate-600">
                {new Date(a.created_at).toLocaleDateString()}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
