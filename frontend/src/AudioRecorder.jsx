import { useState, useRef } from "react";

export default function AudioRecorder() {
  const [status, setStatus] = useState("Idle");
  const [serverResp, setServerResp] = useState(null); // 🟢 state at top level
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);

  // ───── record control ─────
  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(stream);
    mediaRecorder.current.ondataavailable = (e) => chunks.current.push(e.data);
    mediaRecorder.current.onstop = handleStop;
    chunks.current = [];
    mediaRecorder.current.start();
    setStatus("Recording…");
  };

  const stopRecording = () => {
    mediaRecorder.current?.stop();
  };

  // ───── after recording ends ─────
  const handleStop = async () => {
    setStatus("Uploading…");

    const blob = new Blob(chunks.current, { type: "audio/webm" });
    const form = new FormData();
    form.append("file", blob, "hum.webm");

    try {
      const r = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: form,
      });
      const data = await r.json();
      console.log("Server reply:", data);
      setServerResp(data); // save JSON
      setStatus(`Done! Duration ${data.duration_sec.toFixed(2)} s`);
    } catch (err) {
      console.error(err);
      setStatus("Upload failed");
    }
  };

  // ───── UI ─────
  return (
    <div className="space-x-2">
      <button onClick={startRecording} disabled={status === "Recording…"}>
        Start
      </button>
      <button onClick={stopRecording} disabled={status !== "Recording…"}>
        Stop
      </button>
      <span>{status}</span>

      {/* note list */}
      {serverResp && serverResp.notes.length > 0 && (
        <ul style={{ marginTop: "1rem" }}>
          {serverResp.notes.map((n, i) => (
            <li key={i}>
              MIDI {n.midi} — start {n.start.toFixed(2)} s — dur{" "}
              {n.dur.toFixed(2)} s
            </li>
          ))}
        </ul>
      )}
      {serverResp && serverResp.keywords.length > 0 && (
        <p style={{ marginTop: "1rem" }}>
          <strong>Seed words:</strong> {serverResp.keywords.join(", ")}
        </p>
      )}
    </div>
  );
}
