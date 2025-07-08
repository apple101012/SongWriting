"""
lyric.py
--------
Groq-based helpers:
• generate_lyrics (…)     – full draft generator
• regenerate_line (…)     – 3 alt lines, same syllable count
Both now respect a “pinned words” list: words the model must not change.
"""

from __future__ import annotations
import os, re
from typing import List

from groq import Groq   # cloud LLM

# ────────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------- helpers --------------------------------------------
VOWEL_GRP = re.compile(r"[aeiouy]+", re.I)

def count_syllables(text: str) -> int:
    return len(VOWEL_GRP.findall(text.lower()))

def note_groups(notes: List[dict], beat: float = 0.5) -> list[int]:
    """
    Collapse notes that land within `beat` seconds of the previous one.
    Returns syllables per lyric line, e.g. [4, 3, 5, 4].
    """
    if not notes:
        return [4, 4, 4]  # fallback
    groups, cur, t0 = [], [], notes[0]["start"]
    for n in notes:
        if n["start"] - t0 < beat:
            cur.append(n)
        else:
            groups.append(cur); cur = [n]
        t0 = n["start"]
    groups.append(cur)
    return [len(g) for g in groups]

def _pinned_clause(pinned: list[str]) -> str:
    return f"\nDo NOT alter these pinned words: {', '.join(pinned)}." if pinned else ""

# ---------- full-draft generator -------------------------------
def generate_lyrics(
    notes:   list[dict],
    keywords:list[str],
    genre:   str  = "pop",
    n:       int  = 2,
    pinned:  list[str] | None = None,
) -> list[str]:
    pinned = pinned or []
    template = note_groups(notes)
    prompt = f"""
You are a creative songwriting assistant.
Write {n} alternative lyric drafts for a {genre} song.
Each draft must:
- follow this syllable template (per line): {template}
- weave in or riff on these seed words: {', '.join(keywords) or 'anything'}
{_pinned_clause(pinned)}
Return drafts as numbered lines only.
"""
    resp = client.chat.completions.create(
        model       = "llama3-70b-8192",
        temperature = 0.8,
        messages    = [{"role": "user", "content": prompt}],
    )
    text   = resp.choices[0].message.content.strip()
    drafts = re.split(r"^\d+\.\s*", text, flags=re.M)[1:]
    return [d.strip() for d in drafts[:n]]

# ---------- single-line re-writer -------------------------------
PROMPT_TEMPLATE = """
You are a lyric re-writer.
Write exactly THREE alternative lines that:
- each contain exactly {sylls} syllables
- match the genre "{genre}"
- end with the same punctuation (if any){pin_clause}
Return the three lines each on its own line with no numbering.
Old line:
"{original}"
"""

def regenerate_line(
    original: str,
    genre:    str = "pop",
    pinned:   list[str] | None = None,
) -> list[str]:
    pinned = pinned or []
    prompt = PROMPT_TEMPLATE.format(
        original   = original,
        sylls      = count_syllables(original),
        genre      = genre,
        pin_clause = _pinned_clause(pinned),
    )
    resp = client.chat.completions.create(
        model       = "llama3-70b-8192",
        temperature = 0.9,
        messages    = [{"role": "user", "content": prompt}],
    )
    return [l.strip() for l in resp.choices[0].message.content.splitlines() if l.strip()]
