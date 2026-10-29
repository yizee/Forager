"""A local studio for recording the demo narration in your own voice.

Serves video/studio.html on http://localhost:8766, lists the lines of video/forager-demo.srt, and saves each take
as video/voice/NN.wav (16-bit mono WAV, recorded and trimmed in the browser). `node video/make_video.mjs --voice
video/voice` then uses these takes instead of the synthetic voice. Takes stay on this machine (git ignores them).
Run: .venv/bin/python video/voice_studio.py
"""

import json
import re
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE = HERE / "voice"
PORT = 8766


def seconds(stamp: str) -> float:
    hours, minutes, rest = stamp.strip().split(":")
    whole, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000


def take_seconds(path: Path):
    if not path.exists():
        return None
    with wave.open(str(path)) as audio:
        return round(audio.getnframes() / audio.getframerate(), 2)


def lines() -> list[dict]:
    """The narration lines in order, each with the synthetic voice's length and the length of your take, if any."""
    out = []
    for block in re.split(r"\n\s*\n", (HERE / "forager-demo.srt").read_text().strip()):
        rows = block.splitlines()
        start, end = rows[1].split(" --> ")
        n = int(rows[0]) - 1
        out.append({"n": n, "text": " ".join(rows[2:]), "target": round(seconds(end) - seconds(start) - 0.2, 2),
                    "take": take_seconds(VOICE / f"{n:02d}.wav")})
    return out


class Studio(BaseHTTPRequestHandler):
    def reply(self, body: bytes, kind: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json(self, data, status: int = 200):
        self.reply(json.dumps(data).encode(), "application/json", status)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self.reply((HERE / "studio.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/lines":
            self.json(lines())
        elif re.fullmatch(r"/voice/\d{2}\.wav", path) and (VOICE / path.rsplit("/", 1)[1]).exists():
            self.reply((VOICE / path.rsplit("/", 1)[1]).read_bytes(), "audio/wav")
        else:
            self.json({"error": "not found"}, 404)

    def do_POST(self):
        match = re.fullmatch(r"/save/(\d{1,2})", self.path)
        if not match or int(match.group(1)) >= len(lines()):
            return self.json({"error": "no such line"}, 404)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if body[:4] != b"RIFF" or body[8:12] != b"WAVE":
            return self.json({"error": "not a WAV file"}, 400)
        VOICE.mkdir(exist_ok=True)
        path = VOICE / f"{int(match.group(1)):02d}.wav"
        path.write_bytes(body)
        self.json({"n": int(match.group(1)), "take": take_seconds(path)})

    def log_message(self, *args):   # keep the terminal quiet
        pass


if __name__ == "__main__":
    print(f"Narration studio on http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Studio).serve_forever()
