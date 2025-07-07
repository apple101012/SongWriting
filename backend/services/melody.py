"""
melody.py
----------
Hum/recording → list[dict]  (midi, name, start, dur)
Adds latency logs: ffmpeg + pitch.
"""

from pathlib import Path
import os, math, shutil, subprocess, tempfile, time, logging

import numpy as np
import torch
import torchcrepe
import librosa
import soundfile as sf
import warnings, torch
warnings.filterwarnings(
    "ignore",
    message="You are using `torch.load` with `weights_only=False`",
    category=FutureWarning,
    module="torchcrepe",
)


# ───── logger setup ──────────────────────────────────────────────
log = logging.getLogger("latency")
logging.basicConfig(level=logging.INFO, format="[latency] %(message)s")

# ───── constants ────────────────────────────────────────────────
SAMPLE_RATE = 16_000
FRAME_HOP   = 160           # 100 fps

REPO_ROOT = Path(__file__).resolve().parents[2]
EMBEDDED  = REPO_ROOT / "backend" / "bin" / "ffmpeg.exe"
FFMPEG    = str(EMBEDDED) if EMBEDDED.exists() else shutil.which("ffmpeg") or "ffmpeg"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# ───── helpers ──────────────────────────────────────────────────
def midi_to_name(m: int) -> str:
    return f"{NOTE_NAMES[m % 12]}{(m // 12) - 1}"

def hz_to_midi(f):
    return 69 + 12 * np.log2(f / 440.0)

def _webm_to_wav(src: str, dst: str):
    """Convert any audio (webm/wav) → mono 16 kHz wav."""
    subprocess.run(
        [FFMPEG, "-y", "-i", src, "-ac", "1", "-ar", str(SAMPLE_RATE), dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

# ───── core ─────────────────────────────────────────────────────
def extract_notes(audio_path: str):
    # 1) ensure wav 16 kHz
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        _webm_to_wav(audio_path, wav)
        log.info("ffmpeg %.3fs", time.perf_counter() - t0)

        # 2) load
        y, _ = librosa.load(wav, sr=SAMPLE_RATE)

    # 3) pitch tracking (torchcrepe)
    t1 = time.perf_counter()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    audio = torch.as_tensor(y, dtype=torch.float32, device=device).unsqueeze(0)

    f0, pd = torchcrepe.predict(
        audio,
        SAMPLE_RATE,
        hop_length=FRAME_HOP,
        fmin=50, fmax=1050,
        model="full",
        batch_size=1024,
        pad=True,
        return_periodicity=True,
        device=device,
    )
    log.info("pitch  %.3fs", time.perf_counter() - t1)

    f0 = f0.squeeze().cpu().numpy()
    conf = pd.squeeze().cpu().numpy()
    f0[conf < 0.25] = 0
    with np.errstate(divide="ignore"):
        midi = np.where(f0 > 0, np.round(hz_to_midi(f0)), 0).astype(int)

    # 4) group frames → notes
    notes, cur = [], None
    for idx, m in enumerate(midi):
        t = idx * FRAME_HOP / SAMPLE_RATE
        if m == 0:
            if cur:
                cur["dur"] = t - cur["start"]
                notes.append(cur); cur = None
            continue
        if cur and m == cur["midi"]:
            continue
        if cur:
            cur["dur"] = t - cur["start"]
            notes.append(cur)
        cur = {"midi": int(m), "name": midi_to_name(int(m)), "start": t, "dur": 0.0}
    if cur:
        cur["dur"] = len(midi) * FRAME_HOP / SAMPLE_RATE - cur["start"]
        notes.append(cur)

    return notes
