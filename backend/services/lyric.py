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

