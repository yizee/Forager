"""Narration takes from Kokoro-82M (Apache-2.0), an open text-to-speech model that runs locally.

Writes one WAV per line of video/forager-demo.srt, in the format video/make_video.mjs --voice reads, or a short
sample of several voices to choose from. Runs in its own environment so the project's pinned packages stay as
they are; the model files live in video/build/kokoro (both are ignored by git):

  .venv/bin/python -m venv video/build/tts-venv && video/build/tts-venv/bin/pip install kokoro-onnx soundfile
  (model files: kokoro-v1.0.onnx and voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases)

  video/build/tts-venv/bin/python video/tts_kokoro.py --samples af_heart,am_michael --out video/build/samples
  video/build/tts-venv/bin/python video/tts_kokoro.py --voice af_heart --out video/build/voice-af_heart
"""

import argparse
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent
MODELS = HERE / "build" / "kokoro"
SPOKEN = {"Sora 2": "Sora two"}            # how a line is read when the subtitle text would be read wrong
SAMPLE = ("Keeping up with AI news, papers and tools is hard, and most feeds quietly narrow to what you clicked "
          "last week. Forager is a daily brief that stays broad, shows its sources, and asks before it learns.")


def lines() -> list[str]:
    return [" ".join(block.splitlines()[2:]) for block in
            re.split(r"\n\s*\n", (HERE / "forager-demo.srt").read_text().strip())]


def spoken(text: str) -> str:
    for written, said in SPOKEN.items():
        text = text.replace(written, said)
    return text


def trim(samples: np.ndarray, rate: int, pad: float = 0.08) -> np.ndarray:
    """Cut the silence before and after the speech, keeping a little air."""
    level = np.abs(samples)
    loud = np.nonzero(level > max(0.01, level.max() * 0.05))[0]
    if not len(loud):
        return samples
    keep = int(rate * pad)
    return samples[max(0, loud[0] - keep): loud[-1] + keep]


def say(kokoro: Kokoro, text: str, voice: str, speed: float) -> tuple[np.ndarray, int]:
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, rate = kokoro.create(spoken(text), voice=voice, speed=speed, lang=lang)
    return trim(np.asarray(samples, dtype=np.float32), rate), rate


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--voice", help="voice for all narration lines, e.g. af_heart")
    parser.add_argument("--samples", help="comma-separated voices for a sample of each, to choose from")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not (args.voice or args.samples):
        parser.error("give --voice or --samples")
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    args.out.mkdir(parents=True, exist_ok=True)
    if args.samples:
        parts, rate = [], 24000
        for voice in args.samples.split(","):
            name = voice.split("_", 1)[1].capitalize()
            audio, rate = say(kokoro, f"This is {name}. {SAMPLE}", voice, args.speed)
            soundfile.write(args.out / f"{voice}.wav", audio, rate, subtype="PCM_16")
            parts += [audio, np.zeros(int(rate * 0.9), dtype=np.float32)]
            print(f"{voice}: {len(audio) / rate:.1f} s")
        soundfile.write(args.out / "all-voices.wav", np.concatenate(parts), rate, subtype="PCM_16")
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(args.out / "all-voices.wav"),
                        str(args.out / "all-voices.m4a")], check=True)
        return
    total = 0.0
    for n, text in enumerate(lines()):
        audio, rate = say(kokoro, text, args.voice, args.speed)
        soundfile.write(args.out / f"{n:02d}.wav", audio, rate, subtype="PCM_16")
        total += len(audio) / rate
    print(f"{len(lines())} takes in {args.out}, {total:.1f} s of speech ({args.voice}, speed {args.speed})")


if __name__ == "__main__":
    main()
