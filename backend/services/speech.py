from pathlib import Path
import subprocess, tempfile, os, re, collections, torch, librosa
import whisper
from services.melody import FFMPEG, SAMPLE_RATE           # 16 000
os.environ["PATH"] += os.pathsep + str(Path(FFMPEG).parent)

DEVICE  = "cuda" if torch.cuda.is_available() else "cpu"
_model  = whisper.load_model("small", device=DEVICE)      # better accuracy

def _read_mono16k(path: str) -> torch.Tensor:
    """Return 1-D float32 tensor at 16 kHz, normalised to -1..1."""
    # librosa handles WAV / WebM / anything ffmpeg can decode
    y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return torch.from_numpy(y)

def extract_keywords(audio_path: str, top_k: int = 5):
    """Return top-k English seed words from the clip."""
    # ---------- read audio (no external ffmpeg needed) ----------
    samples = _read_mono16k(audio_path)

    # ---------- transcribe on GPU ----------
    result = _model.transcribe(
        audio=samples,
        language="en",
        beam_size=5,                     # better accuracy
        temperature=0.0,
        fp16=(DEVICE == "cuda"),
        verbose=False,
    )
    print("Whisper ran on:", next(_model.parameters()).device)   # should say cuda:0

    # ---------- simple English word filter ----------
    LATIN = re.compile(r"^[a-zA-Z]+$")
    VOWEL = re.compile(r"[aeiou]", re.I)
    words = [
        w.lower().strip(".,?!")
        for w in result["text"].split()
        if len(w) > 2 and LATIN.match(w) and VOWEL.search(w)
    ]
    freq = collections.Counter(words)
    return [w for w, _ in freq.most_common(top_k)]
