"""
speech.py
----------
Whisper → top-k English seed words.
Adds latency log for Whisper inference.
"""

import os, re, time, logging, subprocess, tempfile, torch, whisper
from collections import Counter
from pathlib import Path
from services.melody import FFMPEG, SAMPLE_RATE
os.environ["PATH"] += os.pathsep + str(Path(FFMPEG).parent)
# ───── logger setup ─────────────────────────────────────────────
log = logging.getLogger("latency")   # already configured in melody.py

# ───── load Whisper on GPU if available ─────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_model = whisper.load_model("base", device=DEVICE, in_memory=True)
log.info("Whisper loaded on: %s", next(_model.parameters()).device)

# ───── simple English filters ───────────────────────────────────
LATIN = re.compile(r"^[a-zA-Z]+$")
VOWEL = re.compile(r"[aeiou]", re.I)

def extract_keywords(audio_path: str, top_k: int = 5):
    # 1) convert to wav if needed
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "speech.wav"
        subprocess.run(
            [FFMPEG, "-y", "-i", audio_path, "-ac", "1", "-ar", str(SAMPLE_RATE), wav],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

        # 2) whisper
        t0 = time.perf_counter()
        result = _model.transcribe(
            str(wav),
            language="en",
            fp16=(DEVICE == "cuda")
        )
        log.info("whisper %.3fs", time.perf_counter() - t0)

    # 3) bag-of-words filter
    words = [
        w.lower().strip(".,?!")
        for w in result["text"].split()
        if len(w) > 2 and LATIN.match(w) and VOWEL.search(w)
    ]
    return [w for w, _ in Counter(words).most_common(top_k)]
