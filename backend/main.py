from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import os
from services.speech import extract_keywords  
# 🔑 NEW
from services.melody import extract_notes
from services.lyric import generate_lyrics
app = FastAPI()

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/lyrics")
def make_lyrics(payload: dict):
    """
    Expects: {notes:[…], keywords:[…], genre:str, pinned:[…]}
    """
    drafts = generate_lyrics(
        payload["notes"],
        payload["keywords"],
        payload.get("genre", "pop"),
        3,
        payload.get("pinned", []),
    )
    return {"drafts": drafts}



UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
def read_root():
    return {"msg": "Hello, HumLyric!"}


@app.post("/upload")
async def upload_hum(file: UploadFile = File(...)):
    # 1) save raw WebM
    file_id = f"{uuid4()}.webm"
    dst = UPLOAD_DIR / file_id
    dst.write_bytes(await file.read())

    # 2) 🔑 melody analysis
    notes = extract_notes(str(dst))
    keywords = extract_keywords(str(dst))          # NEW

    duration = round(notes[-1]["start"] + notes[-1]["dur"], 3) if notes else -1.0
    return {
        "file": file_id,
        "duration_sec": duration,
        "keywords": keywords,                      # NEW
        "notes": notes,
    }
    
from services.lyric import regenerate_line   # add to imports


@app.post("/regenerate_line")
def regen(payload: dict):
    """
    Expects: {"line": "...", "genre": "...", "pinned":[...]}
    """
    alts = regenerate_line(
        payload["line"],
        payload.get("genre", "pop"),
        payload.get("pinned", []),
    )
    return {"alts": alts}