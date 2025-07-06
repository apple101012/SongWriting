from pathlib import Path
import subprocess, tempfile
from faster_whisper import WhisperModel
import re
# ── 1. load once (base = good accuracy, cpu-friendly) ────────────
_model = WhisperModel("tiny", device="cpu", compute_type="int8")

# ── 2. helper ────────────────────────────────────────────────────
def extract_keywords(webm_path: str, top_k: int = 5):
    """
    • Converts webm → 16-kHz wav using the same ffmpeg we already bundled.
    • Runs Whisper.
    • Returns up to `top_k` salient words (simple frequency ranking).
    """
    from services.melody import FFMPEG, SAMPLE_RATE           # reuse existing consts
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        subprocess.run(
            [FFMPEG, "-y", "-i", webm_path, "-ac", "1", "-ar", str(SAMPLE_RATE), wav],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

        segments, _ = _model.transcribe(str(wav), vad_filter=True, beam_size=1)

    LATIN_RE = re.compile(r"^[a-zA-Z]+$")        # only ASCII letters
    VOWEL_RE = re.compile(r"[aeiou]", re.I)      # must contain a, e, i, o, or u
    bag = []
    for seg in segments:
        for w in seg.text.split():
            w = w.strip(".,?!").lower()
            if (
                len(w) > 2              # drop “uh”, “yo”, etc.
                and LATIN_RE.match(w)    # only A-Z letters
                and VOWEL_RE.search(w)   # likely pronounceable English
            ):
                bag.append(w)
    # frequency rank (MVP – you can swap in TF-IDF later)
    freq = {}
    for w in bag:
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq, key=freq.get, reverse=True)
    return ranked[:top_k]
