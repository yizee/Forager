"""Build the Critic case set (Stage 4): digests that pass every code rule but contain a
semantic problem that only a reader can see, plus clean controls.

Method: each problem case is a clean base digest with one targeted change. The build
runs forager.checks.check_rules on every case and fails if any rule fires, so by
construction the rules cannot catch these problems. Controls (expected PASS) include
hard negatives: related but distinct items, and distant but legitimate breadth.
One case is the unedited digest from the first live run, with the problems found in it.

Real items are arXiv papers from data/snapshot/arxiv-2026-10-25.json with their
published titles and abstracts. News and repo items are synthetic: fictional names
and example.com links.

Run: .venv/bin/python eval/build_critic_cases.py [out_dir]   (default: eval/cases/critic)
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from forager.checks import check_rules, rule_errors  # noqa: E402

SNAPSHOT = json.loads((ROOT / "data" / "snapshot" / "arxiv-2026-10-25.json").read_text())
LIVE_DIGEST = ROOT / "eval" / "cases" / "critic" / "sources" / "live-digest-2026-10-25.json"
TODAY = "2026-10-25"
ISSUE_TYPES = ("irrelevant_exploration", "near_duplicate", "unsupported_citation",
               "overstated_connection", "mislabeled_interest")
ALL_TYPES = ["paper", "news", "repo"]


# ---- profile ----

def _interest(n, label, facets=(), *, kind="long_term", weight=1.0, expires=None):
    return {"id": f"i{n}", "label": label, "facets": list(facets), "type": kind, "source": "stated",
            "weight": weight, "expires": expires}


def persona(short_term: str) -> dict:
    """The demo persona. With "Sora 2" this is the profile the live digest was made for."""
    return {"interests": [
        _interest(1, "AI agents", ["Agent frameworks and tooling", "Agent benchmarks and evaluation", "Coding agents"]),
        _interest(2, "Video editing", ["AI-assisted editing tools", "Open-source editing pipelines"]),
        _interest(3, "Image generation", ["Diffusion model research", "Controllable generation (editing, inpainting)",
                                          "New model releases"]),
        _interest(4, "AI copyright policy", weight=0.5),
        _interest(5, short_term, kind="short_term", weight=0.8, expires="2026-11-08")],
        "exploration": 0.2}


# ---- items: sources ----

SYNTHETIC = {
    "n01": ("news", "Northwind AI releases Lumen-V 2 video model", "2026-10-24",
            "Northwind AI released Lumen-V 2, a text-to-video model that generates clips of up to 60 seconds at "
            "1080p. The company says the model keeps characters consistent across shots, and API access opens "
            "through a waitlist. No independent evaluation was published with the release."),
    "n02": ("news", "Hands-on: a first look at Lumen-V 2", "2026-10-24",
            "A hands-on review written on Lumen-V 2's release day. The reviewer generated a dozen clips from the "
            "launch demo prompts and describes the 60-second clips and consistent characters that Northwind AI "
            "announced. The review repeats the launch details and adds no measurements."),
    "n03": ("news", "Lumen-V 2 launch recap: everything Northwind announced", "2026-10-25",
            "A recap of Northwind AI's Lumen-V 2 announcement: clips of up to 60 seconds at 1080p, consistent "
            "characters across shots, and an API waitlist. The article summarizes the launch blog post and embeds "
            "the official demo videos."),
    "n04": ("news", "Copyright office opens comment period on AI training opt-outs", "2026-10-23",
            "A national copyright office opened a 60-day public comment period on draft guidance about using "
            "copyrighted images to train AI models. The draft proposes a machine-readable opt-out that rights "
            "holders can attach to their images and asks AI developers to honor it. Final guidance is expected "
            "next year."),
    "n05": ("news", "Harbor Image Cooperative launches opt-in licensing for AI training", "2026-10-22",
            "Harbor Image Cooperative, a stock-photo cooperative, launched a program that lets member photographers "
            "license their images for AI model training and receive a share of the fees. Images are excluded from "
            "training sets unless the photographer opts in."),
    "n06": ("news", "Photographers can now license their work for AI training through Harbor", "2026-10-23",
            "Harbor Image Cooperative's new program lets photographers opt in to licensing their images for AI "
            "training and share in the fees. Images stay out of training sets unless their owners opt in. The "
            "article is based on the cooperative's announcement."),
    "n07": ("news", "Relay 1.0 released: open-source framework for multi-agent workflows", "2026-10-23",
            "The open-source Relay project released version 1.0 of its framework for building multi-agent "
            "workflows. The release adds typed tool definitions, step-level tracing and a replay mode for debugging "
            "agent runs, and the maintainers declare the API stable."),
    "n08": ("news", "Independent test compares Lumen-V 2 with four earlier video models", "2026-10-25",
            "An independent evaluation group compared Lumen-V 2 with four earlier text-to-video models on 200 "
            "prompts. Lumen-V 2 scored highest on temporal consistency but ranked third on prompt adherence. The "
            "group published its prompts and scoring rubric."),
    "n09": ("news", "Cutline video editor adds text-based editing", "2026-10-22",
            "The desktop video editor Cutline added text-based editing: users edit a transcript and the cuts are "
            "applied to the video timeline. The update also adds automatic filler-word removal. The feature is part "
            "of the paid plan."),
    "n10": ("news", "Meridian-XL: open-weight image model released under a permissive license", "2026-10-24",
            "The Meridian project released Meridian-XL, an open-weight text-to-image model, under a permissive "
            "license. The release includes the training code and a model card that lists the licensed datasets "
            "used for training. The maintainers report scores on two public prompt-following benchmarks without "
            "comparing against other models."),
    "n11": ("news", "Learning to insert objects into video by first learning to remove them", "2026-10-24",
            "An article about the UniVOE paper: the researchers train a video object remover first, then use it to "
            "turn real videos into training pairs for inserting objects together with their shadows and other "
            "effects. The article summarizes the paper's comparison with open-source and commercial editing systems."),
    "r01": ("repo", "tidewater-labs/clipforge: transcript-based video cutting", "2026-10-21",
            "clipforge is an open-source pipeline that transcribes a video, lets the user delete sentences from the "
            "transcript, and renders the matching cuts with ffmpeg. The repository gained about 1,200 stars in its "
            "first week. It supports English and Spanish transcription."),
    "r02": ("repo", "agentcheck: a test harness for tool-using agents", "2026-10-20",
            "agentcheck is a lightweight test harness for tool-using LLM agents. It replays recorded tool "
            "responses, checks the agent's actions against expected outcomes and reports pass rates per task. It "
            "has about 800 stars and supports three agent frameworks."),
    "r03": ("repo", "lora-kit: training scripts for image LoRA adapters", "2026-10-19",
            "lora-kit collects training scripts for LoRA adapters on open text-to-image models, with presets for "
            "style and character fine-tuning. It includes dataset captioning helpers and a small evaluation "
            "notebook, and has about 2,000 stars."),
    "r04": ("repo", "awesome-lumen-v2: Lumen-V 2 demos and prompts", "2026-10-25",
            "A curated list of Lumen-V 2 launch demos and the prompts used to make them, collected from Northwind "
            "AI's announcement and social media posts on release day. It adds no tools or evaluations of its own."),
    "r05": ("repo", "dubline: local subtitles and dubbing for video", "2026-10-21",
            "dubline is an open-source tool that generates subtitles with speech recognition, translates them, and "
            "produces a dubbed audio track with voice cloning. It runs locally and exports to common editing formats. The repository "
            "gained about 900 stars this week."),
}


def source(item_id: str) -> dict:
    if item_id.startswith("p"):
        paper = SNAPSHOT[int(item_id[1:]) - 1]
        return {"id": item_id, "type": "paper", "title": paper["title"], "url": paper["url"],
                "published": paper["published"], "source_text": paper["abstract"], "synthetic": False}
    kind, title, published, text = SYNTHETIC[item_id]
    return {"id": item_id, "type": kind, "title": title, "url": f"https://example.com/{kind}/{item_id}",
            "published": published, "source_text": text, "synthetic": True}


# ---- items: how a digest presents them (honest views unless a case overrides) ----

def interest(interest_id, text):
    return {"kind": "interest", "interest_id": interest_id, "text": text}


def breadth(text):
    return {"kind": "breadth", "interest_id": None, "text": text}


VIEWS = {
    "p01": ("FlexPart generates 3D objects part by part from an image and accepts part conditions at different "
            "levels of detail, from sparse points to masks. It reduces part-level error by 10.5% and 16.6% compared "
            "with two recent methods.", ["3D generation"],
            breadth("3D asset generation sits next to your image generation interest and uses similar conditioning ideas.")),
    "p03": ("A survey that treats video understanding and video generation models as models of an underlying world, "
            "organizing work into reading, writing, sharing and interacting with video. It traces a shift toward "
            "persistent state, controllability and physical validity.", ["video models survey"],
            breadth("A map of video understanding and generation research, next to your video editing interest.")),
    "p05": ("SpectralCanary lets a dataset owner check whether a text-to-image model was fine-tuned on their images by "
            "blending a faint low-frequency canary image into each one. It detected dataset use at about 92% true "
            "positives with 1% false positives across five datasets while leaving the images visually unchanged.",
            ["training data auditing", "text-to-image"],
            interest("i4", "Matches AI copyright policy: a technical way to show that images were used for training.")),
    "p08": ("BrickWright gives coding agents a brick-assembly API and a physical-feasibility validator. With these "
            "tools, agents built physically valid models for all 512 test prompts, versus 9-69% validity without them.",
            ["coding agents", "agent tooling"],
            interest("i1", "Matches your Coding agents and Agent frameworks and tooling focus.")),
    "p09": ("EpiSEM-Bench is an executable benchmark of 300 matched unsafe/safe task pairs across six domains that "
            "tests tool-using agents when a tool response omits a safety-relevant fact. Giving agents a way to recover "
            "missing facts reduced unsafe actions for all ten models tested, though agents differed in actually "
            "obtaining the facts.", ["agent benchmarks", "agent safety"],
            interest("i1", "Matches your Agent benchmarks and evaluation focus: a new benchmark for tool-using agents.")),
    "p14": ("UniVOE trains a video object remover, uses it to turn real videos into paired training data, and trains "
            "object insertion on those pairs, so inserted objects come with their motion and interaction effects. "
            "It reports state-of-the-art removal and insertion against open-source and commercial systems.",
            ["video object editing"],
            interest("i2", "Matches Video editing: object removal and insertion in real footage.")),
    "p15": ("WorldForge V2 improves camera control in pretrained video diffusion models with training-free guidance "
            "along a target camera path plus small trajectory adapters. It reports state-of-the-art trajectory "
            "accuracy and quality with very little training data.", ["video generation", "camera control"],
            breadth("Video generation research next to your video editing interest: re-rendering a clip along a new camera path.")),
    "p17": ("A tool-using agent audited the Slovak part of FineWeb2 through a read-only API and turned each finding "
            "into an executable test. Runs costing under $3 found a 1.4-million-document machine-generated content "
            "farm, though a static sampling baseline validated more selectors at under half the cost.",
            ["agent applications", "data quality"],
            interest("i1", "Matches AI agents: an agent used as a debugging tool, with an honest cost comparison.")),
    "p21": ("Bilingual language models trained on a reader's first language predict that reader's English reading "
            "times better than monolingual models, using eye-tracking data from 12 language backgrounds.",
            ["psycholinguistics"], None),
    "p23": ("Simulated control evaluations use a language model to simulate tool responses instead of a real "
            "environment. On LinuxArena they predicted safety with an error of 3.6 percentage points, compared with "
            "10.1 for a separate control setting.", ["agent safety evaluation"],
            interest("i1", "Matches your Agent benchmarks and evaluation focus: a cheaper way to evaluate safeguards for agents.")),
    "p24": ("PC-DAPS keeps several candidate solutions during diffusion posterior sampling and prunes those the "
            "diffusion prior does not support, without ground-truth access. It reduces prior-inconsistent samples on "
            "nonlinear inverse problems such as phase retrieval.", ["diffusion models", "inverse problems"],
            interest("i3", "Matches your Diffusion model research focus.")),
    "p25": ("VERA is an open-source dashboard, deployed at a large European bank, that maps public benchmark results "
            "onto the EU AI Act's measurable technical requirements. In a study it cut the time for a responsible-AI "
            "assessment from 56 to 30 seconds.", ["AI regulation"],
            breadth("AI regulation next to your AI copyright policy interest: how the EU AI Act turns into concrete checks.")),
    "p26": ("Four open language models were tested on 1,552 questions from Spain's MIR medical residency exam, "
            "including whether they recognize uncertain answers and actually use the images they are given.",
            ["medical exams", "LLM evaluation"], None),
    "p28": ("A controlled study of learned unmasking policies for masked diffusion language models, which generate "
            "text tokens in parallel; it identifies which supervision and inputs make a policy worth its overhead.",
            ["diffusion language models"], None),
    "p29": ("Social-HUMINT is a framework for measuring how much an LLM can infer about a person from their social "
            "media posts and how far that profile enables social engineering attacks.",
            ["privacy", "social engineering"], None),
    "p30": ("CellTrack-Bench tests vision-language models on cell tracking in microscopy, with 1,537 problems from 15 "
            "datasets, and compares them with specialized trackers.", ["cell tracking"], None),
    "n01": ("Northwind AI released Lumen-V 2, a text-to-video model for clips of up to 60 seconds at 1080p with "
            "consistent characters across shots. API access opens through a waitlist; no independent evaluation came "
            "with the release.", ["video generation", "model release"],
            interest("i5", "Your short-term focus: the Lumen-V 2 release itself.")),
    "n02": ("A release-day hands-on with Lumen-V 2 that generates clips from the launch demo prompts and describes the "
            "announced 60-second clips and consistent characters.", ["hands-on review"], None),
    "n03": ("A recap of the Lumen-V 2 announcement: 60-second 1080p clips, consistent characters and an API waitlist.",
            ["new model releases"], None),
    "n04": ("A copyright office opened a 60-day comment period on draft guidance that would let rights holders opt "
            "their images out of AI training with a machine-readable signal.", ["training data opt-out"],
            interest("i4", "Matches AI copyright policy: proposed rules on using copyrighted images for AI training.")),
    "n05": ("Harbor Image Cooperative launched opt-in licensing that lets photographers license their images for AI "
            "training and share in the fees; images stay out of training sets unless their owners opt in.",
            ["training data licensing"],
            interest("i4", "Matches AI copyright policy: a licensing model for training data.")),
    "n06": ("Photographers in the Harbor cooperative can opt in to license their images for AI training and share "
            "the fees.", ["creator economy"], None),
    "n07": ("Relay 1.0, an open-source framework for multi-agent workflows, adds typed tool definitions, step-level "
            "tracing and a replay mode for debugging, and declares its API stable.", ["agent frameworks"],
            interest("i1", "Matches your Agent frameworks and tooling focus.")),
    "n08": ("An independent group tested Lumen-V 2 against four earlier video models on 200 prompts: first on temporal "
            "consistency, third on prompt adherence. Prompts and rubric are public.", ["video model evaluation"],
            interest("i5", "Your short-term focus: the first independent measurements of Lumen-V 2.")),
    "n09": ("The Cutline editor added transcript-based editing, where deleting words from the transcript cuts the "
            "video, plus automatic filler-word removal.", ["editing tools"],
            interest("i2", "Matches your AI-assisted editing tools focus.")),
    "n10": ("Meridian-XL, an open-weight text-to-image model, was released under a permissive license with its "
            "training code and a model card listing the licensed training datasets.", ["open image models"],
            interest("i3", "Matches your New model releases focus.")),
    "n11": ("A news write-up of the UniVOE paper: train an object remover first, then use it to create training pairs "
            "for inserting objects with their shadows and effects.", ["AI video effects"],
            interest("i2", "Matches Video editing: realistic object insertion.")),
    "r01": ("clipforge is an open-source pipeline that cuts a video by editing its transcript and renders the cuts with "
            "ffmpeg; it gained about 1,200 stars in its first week.", ["open-source editing pipelines"],
            interest("i2", "Matches your Open-source editing pipelines focus.")),
    "r02": ("agentcheck replays recorded tool responses to test tool-using agents and reports pass rates per task; "
            "about 800 stars.", ["agent evaluation tooling"],
            interest("i1", "Matches your Agent benchmarks and evaluation focus.")),
    "r03": ("lora-kit collects LoRA training scripts for open text-to-image models, with style and character presets "
            "and captioning helpers; about 2,000 stars.", ["fine-tuning tools"],
            interest("i3", "Matches Image generation: practical fine-tuning tools for open models.")),
    "r04": ("A curated list of Lumen-V 2 launch demos and their prompts.", ["community resources"], None),
    "r05": ("dubline creates subtitles, translates them and generates a dubbed voice track locally, exporting to common "
            "editing formats; about 900 stars this week.", ["subtitles and dubbing"],
            interest("i2", "Matches your AI-assisted editing tools focus.")),
}


def item(item_id: str, reason: dict | None = None) -> dict:
    summary, topics, default = VIEWS[item_id]
    reason = reason or default
    if reason is None:
        raise ValueError(f"{item_id} has no default reason; the case must give one.")
    return {**source(item_id), "summary": summary, "topics": topics, "reason": reason}


def point(field, text, *cites):
    return {"text": text, "field": field, "cites": list(cites)}


FIRST = [{"text": "First digest: nothing earlier to compare with.", "cites": []}]


# ---- clean bases ----

def base_a() -> dict:
    ids = ["p09", "p08", "r02", "p14", "r01", "p24", "r03", "p05", "n04", "n01", "p01", "p25"]
    return {"date": TODAY, "items": [item(i) for i in ids], "brief": {
        "points": [
            point("AI agents", "EpiSEM-Bench tests tool-using agents when a tool response leaves out a safety-relevant "
                  "fact; giving agents a way to recover the missing facts reduced unsafe actions for all ten models "
                  "tested.", "p09"),
            point("AI agents", "With BrickWright's assembly API and feasibility validator, coding agents produced "
                  "physically valid brick builds for all 512 test prompts, versus 9-69% validity without the tools.", "p08"),
            point("Video editing", "UniVOE trains video object insertion on pairs created by its own object remover, "
                  "avoiding hard-to-collect paired footage, and reports state-of-the-art removal and insertion.", "p14"),
            point("Video editing", "clipforge, an open-source pipeline that cuts video by editing its transcript, gained "
                  "about 1,200 stars in its first week.", "r01"),
            point("Image generation", "PC-DAPS keeps several candidate solutions during diffusion posterior sampling and "
                  "prunes those the prior does not support, reducing implausible results on problems such as phase "
                  "retrieval.", "p24"),
            point("AI copyright policy", "SpectralCanary lets dataset owners check whether a text-to-image model was "
                  "fine-tuned on their images, detecting use at about 92% true positives with 1% false positives "
                  "across five datasets.", "p05"),
            point("AI copyright policy", "Draft copyright guidance that would let rights holders opt their images out "
                  "of AI training is open for public comment for 60 days.", "n04"),
            point("Lumen-V 2", "Northwind AI released Lumen-V 2, a text-to-video model for clips of up to 60 seconds; "
                  "no independent evaluation came with the release.", "n01"),
        ],
        "connections": [{"text": "FlexPart and UniVOE both let users work on individual parts or objects rather than "
                                 "whole scenes, FlexPart for 3D assets and UniVOE for video.", "cites": ["p01", "p14"]}],
        "changes": FIRST}}


def base_b() -> dict:
    ids = ["p23", "p17", "n07", "n09", "r05", "n10", "r03", "n05", "n08", "p15", "p03"]
    return {"date": TODAY, "items": [item(i) for i in ids], "brief": {
        "points": [
            point("AI agents", "Simulated control evaluations replace the environment with a language model that "
                  "simulates tool responses, and predicted safety on LinuxArena with a 3.6-point error, versus 10.1 "
                  "for a separate control setting.", "p23"),
            point("AI agents", "An agent auditing the Slovak part of FineWeb2 found a 1.4-million-document content farm "
                  "for under $3 per run, though a static sampling baseline validated more selectors at under half "
                  "the cost.", "p17"),
            point("AI agents", "Relay 1.0, an open-source multi-agent framework, adds typed tool definitions, step-level "
                  "tracing and replay for debugging, and declares its API stable.", "n07"),
            point("Video editing", "Cutline added transcript-based editing and filler-word removal, and the open-source "
                  "dubline tool creates translated subtitles and dubbed audio locally.", "n09", "r05"),
            point("Image generation", "Meridian-XL, an open-weight text-to-image model, was released under a permissive "
                  "license with training code and a model card listing its licensed training data.", "n10"),
            point("AI copyright policy", "Harbor Image Cooperative now lets photographers opt in to licensing their "
                  "images for AI training and share in the fees; other images stay out of training sets.", "n05"),
            point("Lumen-V 2", "An independent test on 200 prompts ranked Lumen-V 2 first of five video models on "
                  "temporal consistency but third on prompt adherence.", "n08"),
        ],
        "connections": [{"text": "Meridian-XL's model card lists licensed training data, and Harbor's program creates "
                                 "such licensed images: both are steps toward training image models on licensed data.",
                         "cites": ["n10", "n05"]}],
        "changes": FIRST}}


BASES = {"base-a": base_a, "base-b": base_b}
# Labels a careful reader could reasonably dispute; flags on them are not scored.
# p24: diffusion posterior sampling for inverse problems, filed under Image generation
# through the facet "Diffusion model research"; points[4] is the point that files it there.
BASE_DEBATABLE = {"base-a": ["p24", "points[4]"]}


# ---- edits ----

def swap(digest, old_id, new_item):
    index = next(n for n, i in enumerate(digest["items"]) if i["id"] == old_id)
    digest["items"][index] = new_item


def set_point(digest, index, text, *cites):
    entry = digest["brief"]["points"][index]
    entry["text"] = text
    if cites:
        entry["cites"] = list(cites)


def set_connection(digest, index, text, *cites):
    digest["brief"]["connections"][index] = {"text": text, "cites": list(cites)}


def problem(kind, refs, explanation):
    return {"type": kind, "refs": list(refs), "explanation": explanation}


WHY = {
    "control": "Clean digest: every rule passes and no semantic problem was introduced.",
    "irrelevant_exploration": "No rule judges breadth items against the profile; topic share, coverage, source mix "
                              "and citations are unchanged.",
    "near_duplicate": "Duplicates differ in title, source and topic label, so no rule sees them as the same; no "
                      "topic bucket exceeds 40%.",
    "unsupported_citation": "Every cited ID exists and is included; rules check IDs, not whether the item says what "
                            "the point claims.",
    "overstated_connection": "Connections only need existing citations; whether the link is real cannot be checked "
                             "by a rule.",
    "mislabeled_interest": "Rules trust the interest label the model wrote, for topic share and for coverage.",
}


def build_cases() -> list[dict]:
    cases = []

    def add(case_id, category, base, change, edit=None, problems=(), debatable=(), *, origin="constructed",
            profile=None, digest=None, available_types=ALL_TYPES, history=(), why=None):
        if digest is None:
            digest = BASES[base]()
            if edit:
                edit(digest)
        problem_refs = {ref for entry in problems for ref in entry["refs"]}
        debatable = list(debatable) + [ref for ref in BASE_DEBATABLE.get(base, [])
                                       if ref in refs_in(digest) and ref not in debatable and ref not in problem_refs]
        cases.append({
            "id": case_id, "category": category, "origin": origin, "base": base, "change": change,
            "why_rules_pass": why or WHY[category], "today": TODAY,
            "profile": profile or persona("Lumen-V 2"), "available_types": list(available_types),
            "history": list(history), "digest": digest,
            "expected": {"verdict": "ADJUST" if problems else "PASS", "problems": list(problems),
                         "debatable": list(debatable)}})

    # Controls, including hard negatives.
    add("ctrl-a", "control", "base-a", "None: clean base A.")
    add("ctrl-b", "control", "base-b", "None: clean base B (two distinct video papers as breadth: a method and a survey).")

    def hn01(d):
        swap(d, "r02", item("n08"))
        set_point(d, 7, "Northwind AI released Lumen-V 2 for clips of up to 60 seconds; an independent test on 200 "
                        "prompts then ranked it first on temporal consistency but third on prompt adherence.", "n01", "n08")
    add("hn-01", "control", "base-a", "Hard negative: the Lumen-V 2 launch (n01) and an independent test of the same "
        "model (n08) appear together. Same model, different information: not duplicates.", hn01)
    add("hn-02", "control", "base-b", "Hard negative: breadth item p03 replaced by VERA (p25), an EU AI Act dashboard. "
        "Far from the main topics but honestly justified as next to AI copyright policy.",
        lambda d: swap(d, "p03", item("p25")))

    # Irrelevant exploration.
    add("ie-01", "irrelevant_exploration", "base-a", "Breadth item p25 replaced by CellTrack-Bench (p30), justified "
        "through the word 'tracking'.",
        lambda d: swap(d, "p25", item("p30", breadth(
            "Tracking cells across microscope frames is the same problem as tracking objects when editing video, so "
            "this benchmark speaks to your video editing work."))),
        [problem("irrelevant_exploration", ["p30"], "Cell tracking in microscopy has nothing to do with video "
                 "editing; the shared word 'tracking' is the only link.")])
    add("ie-02", "irrelevant_exploration", "base-b", "Breadth item p03 replaced by a psycholinguistics paper on "
        "second-language reading (p21), linked to agents.",
        lambda d: swap(d, "p03", item("p21", breadth(
            "How language models model human readers could help AI agents understand multilingual users."))),
        [problem("irrelevant_exploration", ["p21"], "A study of human reading times; the link to AI agents is invented.")])
    add("ie-03", "irrelevant_exploration", "base-b", "Breadth item p15 replaced by a medical residency exam study "
        "(p26), linked to image generation.",
        lambda d: swap(d, "p15", item("p26", breadth(
            "Tests whether models actually use the images they are given, which matters for image generation."))),
        [problem("irrelevant_exploration", ["p26"], "About whether exam-answering models read input images, not about "
                 "generating images.")])

    # Near-duplicates under different labels.
    def nd01(d):
        swap(d, "r02", item("n02", interest("i2", "A hands-on look at a new tool for making video clips.")))
        swap(d, "r03", item("n03", interest("i3", "A new model release, which you follow under image generation.")))
        swap(d, "p25", item("r04", breadth("Community resources around a newly released video model.")))
    add("nd-01", "near_duplicate", "base-a", "Three more items about the Lumen-V 2 launch (hands-on n02, recap n03, "
        "demo list r04) replace r02, r03 and p25, each under a different label (i2, i3, breadth).", nd01,
        [problem("near_duplicate", ["n01", "n02", "n03", "r04"], "Four items report the same launch with the same "
                 "facts; one (n01) is enough. Their interest labels are also stretched; a flag on any of these items "
                 "counts toward this problem, not as a false alarm.")])
    add("nd-02", "near_duplicate", "base-b", "Breadth item p03 replaced by a second article on the Harbor licensing "
        "announcement (n06), labeled 'creator economy'.",
        lambda d: swap(d, "p03", item("n06", breadth("How photographers are starting to earn from AI training."))),
        [problem("near_duplicate", ["n05", "n06"], "Two articles about the same Harbor announcement with the same facts.")])

    def nd03(d):
        swap(d, "r01", item("n11"))
        set_point(d, 3, "A new method makes objects inserted into video look realistic, shadows included, by first "
                        "learning to remove them.", "n11")
    add("nd-03", "near_duplicate", "base-a", "clipforge (r01) replaced by a news write-up of the UniVOE paper (n11); "
        "the brief now covers UniVOE twice (points 2 and 3).", nd03,
        [problem("near_duplicate", ["p14", "n11"], "n11 reports the UniVOE paper (p14); the same work appears twice.")])

    # Citations that exist but do not support the point.
    add("uc-01", "unsupported_citation", "base-a", "Point 0 now claims agents act appropriately in every task.",
        lambda d: set_point(d, 0, "EpiSEM-Bench shows that once agents can recover missing facts, they find them and "
                                  "act appropriately in every task."),
        [problem("unsupported_citation", ["points[0]"], "The paper reports that agents differ in whether they obtain "
                 "the missing facts; it does not show appropriate action in every task.")])
    add("uc-02", "unsupported_citation", "base-a", "Point 4 now claims a new open checkpoint beats commercial models, "
        "citing the lora-kit repository (r03).",
        lambda d: set_point(d, 4, "A new open checkpoint now beats commercial image models on prompt following.", "r03"),
        [problem("unsupported_citation", ["points[4]"], "lora-kit is a set of training scripts; it says nothing about "
                 "a checkpoint beating commercial models.")])
    add("uc-03", "unsupported_citation", "base-b", "Point 6 now says Lumen-V 2 ranked first on prompt adherence.",
        lambda d: set_point(d, 6, "An independent test on 200 prompts ranked Lumen-V 2 first of five video models on "
                                  "prompt adherence."),
        [problem("unsupported_citation", ["points[6]"], "The test ranked Lumen-V 2 third on prompt adherence; it was "
                 "first on temporal consistency.")])
    add("uc-04", "unsupported_citation", "base-b", "Point 4 now says Meridian-XL beats earlier open models.",
        lambda d: set_point(d, 4, "Meridian-XL, an open-weight text-to-image model, beats earlier open models on prompt "
                                  "following and comes with a permissive license."),
        [problem("unsupported_citation", ["points[4]"], "The release reports benchmark scores without comparing "
                 "against other models, so 'beats earlier open models' is unsupported.")])

    # Overstated cross-field connections.
    add("oc-01", "overstated_connection", "base-a", "The connection now claims new video models are trained only on "
        "audited data, citing SpectralCanary (p05) and the Lumen-V 2 launch (n01).",
        lambda d: set_connection(d, 0, "SpectralCanary and the Lumen-V 2 release show that new video models are now "
                                       "trained only on audited datasets.", "p05", "n01"),
        [problem("overstated_connection", ["connections[0]"], "Neither item says anything about Lumen-V 2's training "
                 "data; SpectralCanary is about auditing text-to-image fine-tuning.")])
    add("oc-02", "overstated_connection", "base-b", "The connection now claims agents can replace human reviewers.",
        lambda d: set_connection(d, 0, "The FineWeb2 audit and simulated control evaluations together prove that "
                                       "agents can now replace human reviewers in safety audits.", "p17", "p23"),
        [problem("overstated_connection", ["connections[0]"], "The audit relied on a native speaker to validate "
                 "findings, and a cheaper static baseline validated more; simulated control evaluations predict safety "
                 "metrics. Neither shows agents replacing human reviewers.")])
    add("oc-03", "overstated_connection", "base-a", "The connection now claims UniVOE and clipforge are converging.",
        lambda d: set_connection(d, 0, "UniVOE's object editing and clipforge's transcript cutting are converging into "
                                       "a single automated editing pipeline.", "p14", "r01"),
        [problem("overstated_connection", ["connections[0]"], "Two independent projects; nothing in either source "
                 "suggests they are converging.")])

    # Wrong interest labels.
    add("ml-01", "mislabeled_interest", "base-a", "Breadth item p25 replaced by WorldForge V2 (p15) labeled as the "
        "short-term interest Lumen-V 2, as the live run did with Sora 2.",
        lambda d: swap(d, "p25", item("p15", interest("i5", "Advances controllable video generation, the space "
                                                             "Lumen-V 2 occupies."))),
        [problem("mislabeled_interest", ["p15"], "WorldForge V2 is about camera control in video diffusion models in "
                 "general, not about Lumen-V 2.")])
    add("ml-02", "mislabeled_interest", "base-a", "lora-kit (r03) replaced by a study of diffusion language models "
        "(p28) labeled Image generation.",
        lambda d: swap(d, "r03", item("p28", interest("i3", "Matches your Diffusion model research focus: new unmasking "
                                                             "policies for diffusion models."))),
        [problem("mislabeled_interest", ["p28"], "Diffusion language models generate text; the match with image "
                 "generation rests on the word 'diffusion'.")])

    def ml03(d):
        swap(d, "n05", item("p29", interest("i4", "Matches AI copyright policy: rights over the personal information "
                                                  "AI systems extract online.")))
        set_point(d, 5, "Social-HUMINT measures how much LLMs can infer about a person from social media posts and how "
                        "that enables social engineering.", "p29")
        d["brief"]["connections"] = []
    add("ml-03", "mislabeled_interest", "base-b", "The only AI copyright policy item (n05) replaced by Social-HUMINT "
        "(p29), labeled AI copyright policy; the connection that cited n05 is removed.", ml03,
        [problem("mislabeled_interest", ["p29"], "Social-HUMINT is about privacy and social engineering, not copyright. "
                 "Because it carries the i4 label, the coverage rule counts AI copyright policy as covered when it is not.")],
        ["points[5]"],
        why="Rules trust the interest label: here the mislabeled item even satisfies the 7-day coverage rule for "
            "AI copyright policy.")

    # The first live digest, unedited.
    live = json.loads(LIVE_DIGEST.read_text())
    for entry in live["items"]:
        paper = source(entry["id"])
        assert paper["title"] == entry["title"], entry["id"]
        entry.update(source_text=paper["source_text"], synthetic=False)
    add("live-01", "live", None, "None: the digest from the first live run (2026-10-25), unedited.",
        problems=[
            problem("mislabeled_interest", ["p15"], "Labeled Sora 2; the paper is about camera control in video "
                    "diffusion models in general."),
            problem("mislabeled_interest", ["p03"], "Labeled Sora 2; a survey of video world models, not about Sora 2."),
            problem("overstated_connection", ["connections[0]"], "Neither BrickWright nor UniVOE shows that structured "
                    "verification or reciprocal training 'beats scaling raw supervision'."),
            problem("unsupported_citation", ["points[7]"], "The study reports that the instrumental rate rose from "
                    "25.0% to 46.1% around RLVR step 200 before falling to 11.8%; 'no clear evidence that RLVR training "
                    "induces' these behaviours misstates a non-monotonic finding."),
        ],
        debatable=["p01", "p10", "p19", "p02", "p04", "p05", "p14", "points[0]", "points[1]", "points[2]",
                   "points[4]", "connections[1]"],
        origin="live-2026-10-25", profile=persona("Sora 2"),
        digest={"date": live["date"], "items": live["items"], "brief": live["brief"]},
        available_types=["paper"],
        history=[{"date": "2026-10-23", "items": [{"id": "h01", "reason": {"kind": "interest", "interest_id": "i4"}}],
                  "note": "Added so the coverage rule passes; the live run had no history and failed coverage for "
                          "AI copyright policy (i4)."}],
        why="With the history entry, every rule passes (only papers were available, so the source-mix rule does not "
            "apply). Debatable: p01/p10 are 3D generation filed under Image generation, and p05 (dataset auditing) "
            "could belong under AI copyright policy (points 0-2 follow these labels); p19 is RL-trained LLM behaviour "
            "filed under AI agents; p02 (embodied policies) and p04 (pass@k pruning for reasoning models) are breadth "
            "items justified through 'agents', which their sources never mention; p14's reason calls UniVOE "
            "'open-source-style', but the source mentions a proprietary reward model and no code release; point 4 "
            "files WorldForge V2 under Video editing and says it needs no task-specific fine-tuning although it "
            "trains small trajectory adapters; connection 1 says FlexPart avoids retraining, which its abstract does "
            "not say.")
    return cases


# ---- validation and output ----

def refs_in(digest: dict) -> set[str]:
    brief = digest["brief"]
    return ({i["id"] for i in digest["items"]} | {f"points[{n}]" for n in range(len(brief["points"]))}
            | {f"connections[{n}]" for n in range(len(brief.get("connections") or []))})


def validate(case: dict) -> list[str]:
    digest = case["digest"]
    problems = rule_errors(check_rules(digest, case["profile"], {i["id"] for i in digest["items"]},
                                       available_types=case["available_types"], history=case["history"],
                                       today=case["today"]))
    known = refs_in(digest)
    expected = case["expected"]
    for entry in expected["problems"]:
        if entry["type"] not in ISSUE_TYPES:
            problems.append(f"unknown problem type {entry['type']}")
        problems += [f"ref {ref} not in digest" for ref in entry["refs"] if ref not in known]
    problems += [f"debatable ref {ref} not in digest" for ref in expected["debatable"] if ref not in known]
    if (expected["verdict"] == "PASS") != (not expected["problems"]):
        problems.append("verdict does not match problems")
    return problems


def index_markdown(cases: list[dict]) -> str:
    rows = []
    for case in cases:
        expected = case["expected"]
        refs = "; ".join(f"{p['type']}: {', '.join(p['refs'])}" for p in expected["problems"]) or "-"
        rows.append(f"| `{case['id']}` | {case['category']} | {case['base'] or 'live'} | {case['change']} | "
                    f"{expected['verdict']} | {refs} |")
    counts = {}
    for case in cases:
        counts[case["category"]] = counts.get(case["category"], 0) + 1
    summary = ", ".join(f"{name} {count}" for name, count in counts.items())
    return f"""# Critic case set

Digest drafts that pass every code rule in `forager/checks.py` (structure and citation
IDs, topic share <= 40%, 7-day coverage of long-term interests, source-type mix) but
contain a problem that only a reader can see, plus clean controls. They test the
research question for Idea 3: does a Critic add value beyond simple rules?

Generated by `eval/build_critic_cases.py`; do not edit the JSON files by hand. The build
fails if any rule fires on a case or if a ground-truth reference does not exist.

{len(cases)} cases: {summary}.

## How the cases were made

- **Problem cases** are a clean base digest (`base-a` or `base-b`) with one targeted
  change, so each tests one problem. `live-01` is the unedited digest from the first live
  run (see `docs/live-runs.md`), with the problems found in it.
- **Controls** expect PASS. `hn-01` and `hn-02` are hard negatives: two items about the
  same model that carry different information, and distant but honestly justified breadth.
- **Items**: papers are real arXiv entries from `data/snapshot/arxiv-2026-10-25.json`
  (published titles and abstracts, `synthetic: false`). News and repo items are
  synthetic, with fictional names and example.com links (`synthetic: true`). Each item's
  `source_text` is what the Critic should check claims against.
- **Profile**: the demo persona; its short-term interest is the fictional Lumen-V 2 in
  constructed cases and Sora 2 in `live-01` (the profile the live digest was made for).
- **Debatable labels**: a few labels a careful reader could reasonably dispute are listed
  in `expected.debatable` and not scored either way. Every case built on `base-a` lists
  p24 (diffusion posterior sampling for inverse problems, filed under Image generation
  through the facet "Diffusion model research") and points[4], which files it there;
  `live-01` lists several (see its `why_rules_pass`).

## Ground truth and scoring

`expected.verdict` is PASS or ADJUST. Each entry in `expected.problems` has a type
({", ".join(ISSUE_TYPES)}), the refs it concerns (item IDs, `points[i]`, `connections[i]`)
and an explanation. Proposed scoring for the Stage 5 evaluation:

- A problem is **caught** when the Critic says ADJUST and one of its issues names one of
  the problem's refs (for `near_duplicate`, at least two refs of the group). Matching the
  problem type is reported separately.
- Issues that name only debatable refs are ignored. Any other flagged ref that is not a
  problem ref is a **false alarm**, so an ADJUST on a control is a false alarm unless all
  its issues name only debatable refs.
- Rules-only flags nothing on any case, by construction.

## Label audit (2026-10-26)

Labels were written by Claude while constructing the cases, then audited twice: by Claude
against every source text, and by an independent reviewer (a separate Claude agent that
saw only the case files and the Critic's definitions, not the first audit). Both found
the first two problems below on their own. Changes made:

- `live-01` points[7] became a problem (unsupported_citation): the OLMo-3 study reports the
  instrumental rate rising from 25.0% to 46.1% before falling, not "no clear evidence".
- Base A: n04 was about labeling AI-generated images but was filed under AI copyright
  policy; it is now a copyright item (training opt-outs). Base B: point 3 called dubline
  open-source, which its source did not say; the source now says so.
- Base A: "GitHub stars" became "stars" (the source does not say GitHub); FlexPart's
  "10-17%" became the exact 10.5% and 16.6%; UniVOE's summary no longer adds "shadows".
- Debatable additions: points[4] in base-A cases (it files p24); p04 and p14 in `live-01`.
- The Critic now sees each source text in full (up to 2,000 characters); before, 15 of 30
  abstracts were cut at 1,500.

Kept on purpose: in `nd-01` the duplicate items also carry stretched interest labels;
they are not separate problems, but a flag on them counts toward the duplicate problem.
SpectralCanary filed under AI copyright policy (base A) is kept as correct.

The project author's own check is still pending.

## Cases

| Case | Category | Base | Change | Expected | Problems |
| --- | --- | --- | --- | --- | --- |
""" + "\n".join(rows) + "\n"


def main(out: Path) -> None:
    cases = build_cases()
    failures = {case["id"]: errors for case in cases if (errors := validate(case))}
    if failures:
        raise SystemExit(f"Invalid cases: {json.dumps(failures, indent=2)}")
    out.mkdir(parents=True, exist_ok=True)
    for case in cases:
        (out / f"{case['id']}.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n")
    (out / "README.md").write_text(index_markdown(cases))
    print(f"Wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "eval" / "cases" / "critic")
