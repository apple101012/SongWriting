import { useState } from "react";

export default function AltMenu({ line, pinned, genre, onPick }) {
  const [alts, setAlts] = useState(null);
  const [loading, setLoading] = useState(false);

  async function fetchAlts() {
    setLoading(true);
    const r = await fetch("http://127.0.0.1:8000/regenerate_line", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ line, genre, pinned }),
    });
    const { alts } = await r.json();
    setAlts(alts);
    setLoading(false);
  }

  if (!alts)
    return (
      <button className="text-blue-600 underline" onClick={fetchAlts}>
        {loading ? "..." : "Regenerate"}
      </button>
    );

  return (
    <div className="space-y-1 bg-white border p-2 shadow-md rounded">
      {alts.map((a, i) => (
        <div
          key={i}
          className="cursor-pointer hover:bg-blue-50 px-1"
          onClick={() => onPick(a)}
        >
          {a}
        </div>
      ))}
    </div>
  );
}
