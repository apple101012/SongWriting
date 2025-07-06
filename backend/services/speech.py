from pathlib import Path
import subprocess, tempfile, os, re, collections, torch
import whisper

from services.melody import FFMPEG, SAMPLE_RATE

# ── make sure ffmpeg.exe can be found ──────────────────────────────
os.environ["PATH"] += os.pathsep + str(Path(FFMPEG).parent)

# ── choose device ──────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── load Whisper once, on the right device ─────────────────────────
_model = whisper.load_model("base", device=DEVICE)

def extract_keywords(webm_path: str, top_k: int = 5):
    """Return up to `top_k` English seed words detected in the clip."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        # WebM → WAV
        subprocess.run(
            [FFMPEG, "-y", "-i", webm_path, "-ac", "1", "-ar", str(SAMPLE_RATE), wav],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        # transcribe
        result = _model.transcribe(
            str(wav),
            language="en",
            fp16=(DEVICE == "cuda"),  # half-precision on GPU
            verbose=False,
        )

    # debug: confirm GPU/CPU
    print("Whisper ran on:", next(_model.parameters()).device)

    # bag-of-words filter (English-looking)
    LATIN = re.compile(r"^[a-zA-Z]+$")
    VOWEL = re.compile(r"[aeiou]", re.I)

    words = [
        w.lower().strip(".,?!")
        for w in result["text"].split()
        if len(w) > 2 and LATIN.match(w) and VOWEL.search(w)
    ]
    freq = collections.Counter(words)
    return [w for w, _ in freq.most_common(top_k)]
