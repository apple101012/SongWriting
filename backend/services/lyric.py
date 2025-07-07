# backend/services/lyric.py
import os, re, collections, asyncio
from groq import Groq                                           # cloud LLM
from typing import List

# ────────────  set up Groq client  ────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ────────────  helper: basic syllable counter  ────────────
VOWELS = "aeiouy"

def syllables(word: str) -> int:
    word = word.lower()
    parts = re.findall(r"[aeiouy]+", word)
    return max(1, len(parts))

# ────────────  helper: notes → syllable template  ────────────
def note_groups(notes: List[dict], beat: float = 0.5) -> list[int]:
    """
    Collapse notes that land within `beat` seconds of the previous one.
    Returns a list like [4, 3, 4, 5]  (syllables per lyric line)
    """
    if not notes:
        return [4, 4, 4]   # fallback
    groups, cur, t0 = [], [], notes[0]["start"]
    for n in notes:
        if n["start"] - t0 < beat:
            cur.append(n)
        else:
            groups.append(cur)
            cur = [n]
        t0 = n["start"]
    groups.append(cur)
    return [len(g) for g in groups]

# ────────────  main function called by FastAPI  ────────────
# ... all code stays the same up to generate_lyrics

def generate_lyrics(notes, keywords, genre="pop", n=2):   # ← removed async
    template = note_groups(notes)
    prompt = f"""
You are a creative songwriting assistant.
Write {n} alternative lyric drafts for a {genre} song.
Each draft must:
- follow this syllable template (per line): {template}
- weave in or riff on these seed words: {', '.join(keywords) or 'anything'}
Return drafts as numbered lines.
"""
    resp = client.chat.completions.create(                # ← no await
        model      = "llama3-70b-8192",
        temperature= 0.8,
        messages   = [{"role":"user","content":prompt}]
    )
    text   = resp.choices[0].message.content.strip()
    drafts = re.split(r"^\d+\.\s*", text, flags=re.M)[1:]
    return [d.strip() for d in drafts[:n]]

def count_syllables(line: str) -> int:
    """Very rough syllable estimator (vowels groups)."""
    return len(re.findall(r"[aeiouy]+", line.lower()))

PROMPT_TEMPLATE = """
You are a lyric re-writer.
Write exactly THREE alternative lines that:
- each contain exactly {sylls} syllables
- match the genre "{genre}"
- end with the same punctuation (if any)
Return the three lines each on its own line with no numbering.
Old line:
"{original}"
"""

def regenerate_line(original: str, genre: str = "pop") -> List[str]:
    """
    Return three alternative lines with identical syllable count.
    Blocking (non-async) call, just like generate_lyrics().
    """
    sylls  = count_syllables(original)
    prompt = PROMPT_TEMPLATE.format(original=original, sylls=sylls, genre=genre)

    resp = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )

    return [
        l.strip()
        for l in resp.choices[0].message.content.splitlines()
        if l.strip()
    ]