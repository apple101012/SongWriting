import { useState, useRef } from "react";

const WAV_MIME = "audio/wav";
const WAV_OK = MediaRecorder.isTypeSupported(WAV_MIME);

export default function AudioRecorder() {
  const [status, setStatus] = useState("Idle");
  const [resp, setResp] = useState(null); // server reply from /upload
  const [lyrics, setLyrics] = useState(null); // ← NEW: drafts array
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);

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
          <ul>
            {resp.notes.map((n, i) => (
              <li key={i}>
                MIDI {n.midi} — {n.start.toFixed(2)}-
                {(n.start + n.dur).toFixed(2)} s
              </li>
            ))}
          </ul>
        </>
      )}

      {lyrics && (
        <div>
          <h3 className="mt-4 font-bold">Lyric drafts</h3>
          {lyrics.map((d, i) => (
            <pre
              key={i}
              className="bg-gray-100 p-2 rounded mb-2 whitespace-pre-wrap"
            >
              {d}
            </pre>
          ))}
        </div>
      )}
    </div>
  );
}
