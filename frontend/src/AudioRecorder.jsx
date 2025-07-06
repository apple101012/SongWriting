// frontend/src/AudioRecorder.jsx
import { useState, useRef } from "react";

const WAV_MIME = "audio/wav"; // 48-kHz PCM from Chrome
const WAV_SUPPORTED = MediaRecorder.isTypeSupported(WAV_MIME);

export default function AudioRecorder() {
  const [status, setStatus] = useState("Idle");
  const [serverResp, setServerResp] = useState(null);
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const options = WAV_SUPPORTED ? { mimeType: WAV_MIME } : {}; // fallback → webm
    mediaRecorder.current = new MediaRecorder(stream, options);
    mediaRecorder.current.ondataavailable = (e) => chunks.current.push(e.data);
    mediaRecorder.current.onstop = handleStop;
    chunks.current = [];
    mediaRecorder.current.start();
    setStatus("Recording…");
  };

  const stopRecording = () => mediaRecorder.current?.stop();

  async function handleStop() {
    setStatus("Uploading…");
    const ext = WAV_SUPPORTED ? "wav" : "webm";
    const blob = new Blob(chunks.current, {
      type: WAV_SUPPORTED ? WAV_MIME : "audio/webm",
    });
    const form = new FormData();
    form.append("file", blob, `hum.${ext}`);

    try {
      const r = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: form,
      });
      const data = await r.json();
      setServerResp(data);
      setStatus(`Done! Duration ${data.duration_sec.toFixed(2)} s`);
    } catch (err) {
      console.error(err);
      setStatus("Upload failed");
    }
  }

  return (
    <div className="space-x-2">
      <button onClick={startRecording} disabled={status === "Recording…"}>
        Start
      </button>
      <button onClick={stopRecording} disabled={status !== "Recording…"}>
        Stop
      </button>
      <span>{status}</span>

      {serverResp && serverResp.notes.length > 0 && (
        <>
          <p>
            <strong>Seed words:</strong> {serverResp.keywords.join(", ")}
          </p>
          <ul>
            {serverResp.notes.map((n, i) => (
              <li key={i}>
                MIDI {n.midi} — {n.start.toFixed(2)}-
                {(n.start + n.dur).toFixed(2)} s
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
