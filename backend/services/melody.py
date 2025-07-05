import subprocess, uuid, os, math, json, tempfile
import numpy as np
import torch
import torchcrepe
import librosa

from pathlib import Path, PureWindowsPath
import shutil, subprocess, tempfile, math, os, numpy as np, torch, torchcrepe, librosa

# locate ffmpeg:
REPO_ROOT = Path(__file__).resolve().parents[2]      # adjust depth if needed
EMBEDDED = REPO_ROOT / "backend" / "bin" / "ffmpeg.exe"
FFMPEG = str(EMBEDDED) if EMBEDDED.exists() else shutil.which("ffmpeg") or "ffmpeg"

SAMPLE_RATE = 16000
FRAME_HOP   = 160

def _webm_to_wav(src_path: str, dst_path: str):
    subprocess.run(
        [FFMPEG, "-y", "-i", src_path, "-ac", "1", "-ar", str(SAMPLE_RATE), dst_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def hz_to_midi(f):
    """Vectorized Hz→MIDI conversion (f can be float or ndarray)."""
    return 69 + 12 * np.log2(f / 440.0)


def extract_notes(webm_path: str):
    # 1) convert to wav in tmp dir
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        _webm_to_wav(webm_path, wav)

        # 2) load
        y, sr = librosa.load(wav, sr=SAMPLE_RATE)

    # 3) pitch track (torchcrepe)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    f0, pd = torchcrepe.predict(
        torch.tensor(y).unsqueeze(0).to(device),
        SAMPLE_RATE,
        hop_length=FRAME_HOP,
        fmin=50, fmax=1050,
        model="full",
        batch_size=1024,
        pad=True,
        return_periodicity=True,     # ← add this
    )

    f0 = f0.squeeze().cpu().numpy()          # Hz
    confidence = pd.squeeze().cpu().numpy()  # probability voiced

    # 4) clean up: ignore low-confidence frames
    f0[confidence < 0.25] = 0.0

    # 5) quantize to midi ints, 0 for unvoiced
    midi = np.where(f0 > 0, np.round(hz_to_midi(f0)), 0).astype(int)

    # 6) group consecutive identical midi numbers into note spans
    notes = []
    cur = None
    for idx, m in enumerate(midi):
        t = idx * FRAME_HOP / SAMPLE_RATE  # seconds

        if m == 0:
            # gap; close any running note
            if cur:
                cur["dur"] = t - cur["start"]
                notes.append(cur); cur = None
            continue

        if cur and m == cur["midi"]:
            continue  # extend current note
        else:
            # close old
            if cur:
                cur["dur"] = t - cur["start"]
                notes.append(cur)
            # start new
            cur = {"midi": int(m), "start": t, "dur": 0.0}

    if cur:  # tail
        cur["dur"] = len(midi) * FRAME_HOP / SAMPLE_RATE - cur["start"]
        notes.append(cur)

    return notes
