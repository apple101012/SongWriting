import { useState, useRef } from "react";
import AltMenu from "./AltMenu";

const WAV_MIME = "audio/wav";
const WAV_OK = MediaRecorder.isTypeSupported(WAV_MIME);

export default function AudioRecorder() {
  const [status, setStatus] = useState("Idle");
  const [resp, setResp] = useState(null); // server reply from /upload
  const [lyrics, setLyrics] = useState(null); // ← NEW: drafts array
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const [selLine, setSelLine] = useState(null); // currently clicked line idx

  // ────────── record control ──────────
  const startRec = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(
      stream,
      WAV_OK ? { mimeType: WAV_MIME } : {}
    );
    mediaRecorder.current.ondataavailable = (e) => chunks.current.push(e.data);
    mediaRecorder.current.onstop = handleStop;
    chunks.current = [];
    mediaRecorder.current.start();
    setStatus("Recording…");
  };
  const stopRec = () => mediaRecorder.current?.stop();

  // ────────── upload after stop ──────────
  async function handleStop() {
    setStatus("Uploading…");
    const blob = new Blob(chunks.current, {
      type: WAV_OK ? WAV_MIME : "audio/webm",
    });
    const form = new FormData();
    form.append("file", blob, `hum.${WAV_OK ? "wav" : "webm"}`);

    try {
      const r = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: form,
      });
      const data = await r.json();
      setResp(data); // save notes + keywords
      setStatus("Uploaded ✓");
      setLyrics(null); // clear old drafts
    } catch (e) {
      console.error(e);
      setStatus("Upload failed");
    }
  }

  // ────────── call /lyrics ──────────
  async function generateLyrics() {
    if (!resp) return;
    setStatus("Thinking…");
    try {
      const r = await fetch("http://127.0.0.1:8000/lyrics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes: resp.notes,
          keywords: resp.keywords,
          genre: "folk",
        }),
      });
      const { drafts } = await r.json();
      setLyrics(drafts);
      setStatus("Done ✓");
    } catch (e) {
      console.error(e);
      setStatus("Lyric failed");
    }
  }

  // ────────── UI ──────────
  return (
    <div className="space-y-3">
      <div className="space-x-2">
        <button onClick={startRec} disabled={status === "Recording…"}>
          Start
        </button>
        <button onClick={stopRec} disabled={status !== "Recording…"}>
          Stop
        </button>
        <button onClick={generateLyrics} disabled={!resp}>
          Generate Lyrics
        </button>
        <span>{status}</span>
      </div>

      {resp && (
        <>
          <p>
            <strong>Seed words:</strong> {resp.keywords.join(", ")}
          </p>
          {resp && resp.notes.length > 0 && (
            <table className="mt-4 text-sm">
              <thead>
                <tr>
                  <th className="px-2 text-left">Note</th>
                  <th className="px-2 text-left">Start&nbsp;(s)</th>
                  <th className="px-2 text-left">Len&nbsp;(s)</th>
                  <th className="px-2">▶︎</th>
                </tr>
              </thead>
              <tbody>
                {resp.notes.map((n, i) => (
                  <tr key={i}>
                    <td className="px-2">
                      {n.name} <span className="text-gray-400">({n.midi})</span>
                    </td>
                    <td className="px-2">{n.start.toFixed(2)}</td>
                    <td className="px-2">{n.dur.toFixed(2)}</td>
                    {/* tiny piano-roll bar */}
                    <td>
                      <div
                        style={{
                          width: `${(n.dur * 80).toFixed(0)}px`,
                          height: "6px",
                          background: "#60a5fa",
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {lyrics && (
        <div>
          <h3 className="mt-4 font-bold">Lyric drafts</h3>
          {lyrics.map((text, i) => (
            <div key={i} className="mb-3 space-y-1">
              {text.split("\n").map((ln, j) => (
                <div key={j}>
                  <span
                    onClick={() => setSelLine(`${i}-${j}`)}
                    className="cursor-pointer hover:bg-yellow-100"
                  >
                    {ln || "\u00A0"}
                  </span>
                  {selLine === `${i}-${j}` && (
                    <AltMenu
                      line={ln}
                      onPick={(newLine) => {
                        // replace the line
                        const newDraft = text.split("\n");
                        newDraft[j] = newLine;
                        const next = [...lyrics];
                        next[i] = newDraft.join("\n");
                        setLyrics(next);
                        setSelLine(null);
                      }}
                    />
                  )}
                </div>
              ))}
              <button onClick={() => playDraft(text)}>
                ▶ Hear draft {i + 1}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
