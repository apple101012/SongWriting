# services/lyric.py  (append at bottom)

from typing import List
from groq import Groq         # already installed
import os, re

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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

async def regenerate_line(original: str, genre: str) -> List[str]:
    sylls = count_syllables(original)
    prompt = PROMPT_TEMPLATE.format(original=original, sylls=sylls, genre=genre)

    resp = await _client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    # split into 3 lines, trim blanks
    return [l.strip() for l in resp.choices[0].message.content.splitlines() if l.strip()]
