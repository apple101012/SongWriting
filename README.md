# HumLyric - AI-Assisted Songwriting Tool

HumLyric is an intelligent lyric-writing assistant that helps artists craft meaningful and rhythmically sound lyrics using AI. You provide seed words or syllable structures, and the tool generates lyrical drafts that follow your style and constraints.

---

## Features

- AI-powered lyric generation using Groq's large language models
- Syllable-aware prompts to guide rhythmic accuracy
- Pinned words to enforce topic consistency across lines
- Regenerates lyrics on demand with stylistic variance
- Stores multiple drafts for review or editing

---

## Tech Stack

- Backend: Python
  - `groq` API for LLM access
  - Custom syllable counter (vowel-based pattern detection)
  - Async generation pipeline
- Frontend: (optional — React, Flask, etc.)

---

## Getting Started

1. Clone the repository
```bash
git clone https://github.com/yourusername/humlyric.git
cd humlyric
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set your Groq API key
```bash
export GROQ_API_KEY=your-api-key
```

4. Run the server
```bash
python main.py
```

---

## File Overview

| File                  | Purpose                                                |
|-----------------------|--------------------------------------------------------|
| `services/lyric.py`   | Core logic for generating lyrics                      |
| `utils/syllables.py`  | Syllable counter for rhythm shaping                   |
| `main.py`             | Entry point for testing lyric prompts                 |
| `requirements.txt`    | Python dependencies                                   |

---

## Prompt Design

The system uses:
- Seed words for inspiration (e.g., jot, drop, let)
- Pinned words to anchor recurring themes
- Syllable count templates to structure verses (like melody scaffolding)

### Example Output:
```
In the stillness, I'll inscribe your name in journal  
Jot it down in my journal, next to things I’ll do  
That summer breeze, it whispers low and sweet  
```

---

## To-Do / Future Ideas

- [ ] Add rhyme-scheme detection
- [ ] UI for interactive line editing
- [ ] Melody input → automatic syllable template generation
- [ ] Export lyrics to `.txt` or `.lrc` file

---

## Author

Built by Shihab Jamal  
Inspired by the intersection of music, language, and AI.

---

## License

MIT License – do what you want with it, just give credit.
