# backend/services/melody.py
#
# Hums → note list (pitch + timing)  -----------------------------
# • Converts incoming WebM/WAV to mono-16 kHz WAV (ffmpeg or copy)
# • Runs torchcrepe for f0 tracking (GPU if available)
# • Cleans low-confidence frames, quantises to MIDI integers
# • Groups consecutive identical MIDI numbers into note spans
# • Adds human-readable note names (C4, F#2, …)
# ----------------------------------------------------------------

import os, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np
import torch, torchcrepe, librosa

# ─── locate ffmpeg ───────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]        # adjust depth if layout changes
EMBEDDED  = REPO_ROOT / "backend" / "bin" / "ffmpeg.exe"
FFMPEG    = str(EMBEDDED) if EMBEDDED.exists() else (shutil.which("ffmpeg") or "ffmpeg")

# ─── audio constants ────────────────────────────────────────────
SAMPLE_RATE = 16_000            # Hz
FRAME_HOP   = 160               # 100 FPS for torchcrepe

# ─── helper: convert only when needed ────────────────────────────
def _webm_to_wav(src_path: str, dst_path: str) -> None:
    """Ensure mono 16-kHz WAV at dst_path."""
    if src_path.lower().endswith(".wav"):
        shutil.copy(src_path, dst_path)
        return
    subprocess.run(
        [FFMPEG, "-y", "-i", src_path, "-ac", "1", "-ar", str(SAMPLE_RATE), dst_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

# ─── note-name helpers ───────────────────────────────────────────
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

def midi_to_name(m: int) -> str:
    return f"{NOTE_NAMES[m % 12]}{(m // 12) - 1}"       # MIDI 60 → C4

def hz_to_midi(f):
    """Vectorised Hz→MIDI; skips zeros to avoid log2(-inf) runtime warnings."""
    f = np.where(f == 0, np.nan, f)
    midi = 69 + 12 * np.log2(f / 440.0)
    return np.nan_to_num(midi, nan=0)

# ─── main entry point ────────────────────────────────────────────
def extract_notes(audio_path: str) -> list[dict]:
    """
    Returns a list of dicts:
      { "midi": 49, "name": "A#2", "start": 0.50, "dur": 0.06 }
    """
    # 1) convert to WAV in a tmp dir
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        _webm_to_wav(audio_path, wav)

        # 2) load signal
        y, _ = librosa.load(wav, sr=SAMPLE_RATE, mono=True)

    # 3) torchcrepe pitch tracking
    device = "cuda" if torch.cuda.is_available() else "cpu"
    f0, pd = torchcrepe.predict(
        torch.tensor(y).unsqueeze(0).to(device),
        SAMPLE_RATE,
        hop_length=FRAME_HOP,
        fmin=50,
        fmax=1050,
        model="full",
        batch_size=1024,
        pad=True,
        return_periodicity=True,
    )
    f0          = f0.squeeze().cpu().numpy()            # Hz
    confidence  = pd.squeeze().cpu().numpy()

    # 4) zero-out low-confidence frames
    f0[confidence < 0.25] = 0.0

    # 5) quantise to MIDI ints (0 for unvoiced)
    midi = np.where(f0 > 0, np.round(hz_to_midi(f0)), 0).astype(int)

    # 6) group consecutive identical MIDI numbers
    notes, cur = [], None
    for idx, m in enumerate(midi):
        t = idx * FRAME_HOP / SAMPLE_RATE  # seconds

        if m == 0:                          # silence frame
            if cur:                         # close running note
                cur["dur"] = t - cur["start"]
                notes.append(cur)
                cur = None
            continue

        if cur and m == cur["midi"]:
            continue                        # extend current note

        # close previous if pitch changed
        if cur:
            cur["dur"] = t - cur["start"]
            notes.append(cur)

        # start new note
        cur = {
            "midi":  int(m),
            "name":  midi_to_name(int(m)),
            "start": t,
            "dur":   0.0,
        }

    # tail note
    if cur:
        cur["dur"] = len(midi) * FRAME_HOP / SAMPLE_RATE - cur["start"]
        notes.append(cur)

    return notes
