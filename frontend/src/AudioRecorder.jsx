import { useState, useRef, useEffect } from "react";
import AltMenu from "./AltMenu";

const WAV_MIME = "audio/wav";
const WAV_OK = MediaRecorder.isTypeSupported(WAV_MIME);

export default function AudioRecorder() {
  const [status, setStatus] = useState("Idle");
  const [resp, setResp] = useState(null); // /upload reply
  const [lyrics, setLyrics] = useState(null); // drafts array
  const [pinned, setPinned] = useState([]); // ← pinned words
  const [selLine, setSelLine] = useState(null); // "draftIdx-lineIdx"

  const mediaRecorder = useRef(null);
  const chunks = useRef([]);

  // ---------- recording ---------------------------------------
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

  // ---------- upload ------------------------------------------
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
      setResp(data);
      setStatus("Uploaded ✓");
      setLyrics(null);
      setPinned([]);
    } catch (e) {
      console.error(e);
      setStatus("Upload failed");
    }
  }

  // ---------- full-draft generation ---------------------------
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
          pinned,
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

  // ---------- pin/unpin a word --------------------------------
  function togglePin(word) {
    setPinned((prev) =>
      prev.includes(word) ? prev.filter((w) => w !== word) : [...prev, word]
    );
  }

  // ---------- UI ----------------------------------------------
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
          {/* notes table omitted for brevity */}
        </>
      )}

      {/* lyric drafts */}
      {lyrics && (
        <div>
          <h3 className="mt-4 font-bold">Lyric drafts</h3>

          {pinned.length > 0 && (
            <p className="text-sm mb-2">
              <strong>Pinned:</strong> {pinned.join(", ")}
            </p>
          )}

          {lyrics.map((text, i) => (
            <div key={i} className="mb-4 space-y-1 relative">
              {text.split("\n").map((ln, j) => (
                <div key={j} className="flex items-start gap-1 group">
                  {/* words with spacing + pin toggle */}
                  {ln
                    .split(" ")
                    .map((w, k) => (
                      <span
                        key={k}
                        onClick={() => togglePin(w)}
                        className={
                          "cursor-pointer select-none" +
                          (pinned.includes(w)
                            ? " bg-green-200 rounded px-0.5"
                            : " hover:bg-yellow-100")
                        }
                      >
                        {w}
                      </span>
                    ))
                    .flatMap((el, idx, arr) =>
                      idx < arr.length - 1 ? [el, " "] : [el]
                    )}

                  {/* small edit icon (shows on hover) */}
                  <button
                    onClick={() => setSelLine(`${i}-${j}`)}
                    className="invisible group-hover:visible text-blue-500 ml-2"
                  >
                    ✎
                  </button>

                  {/* alt-menu */}
                  {selLine === `${i}-${j}` && (
                    <AltMenu
                      line={ln}
                      genre="folk"
                      pinned={pinned}
                      onPick={(newLine) => {
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
