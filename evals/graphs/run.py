#!/usr/bin/env python3
"""Graph eval: the same five graphs drawn seven ways by several models, checked by code and by a blind judge.

Arms:  A   today's Graph spec + `us graph`            B   upgraded spec + draw_b.py     B2  B + one look-and-fix round
       C0  the model writes SVG, told only the result  C   SVG with method rules         D   C + one look-and-fix round
       E   the model has a shell and picks its own software
Needs the `claude` CLI and runs models, so it is a periodic eval, not a unit test.
Usage: uv run --with resvg_py --with pillow --with matplotlib python evals/graphs/run.py OUT_DIR [gen fix judge report]
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check as checker  # noqa: E402
import draw_b  # noqa: E402

US = HERE.parents[1] / "plugins" / "unistudent" / "scripts" / "us.py"
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5", "fable": "claude-fable-5-2"}
JUDGE = "claude-sonnet-5-5"  # the size the plugin's own verifier runs on (ADR 0016)
SYSTEM = "You write study material for a university course taught in Hebrew. Follow the instructions exactly."
HEAD = ("Reproduce this graph from the course for a study pack. The student will compare your graph with the "
        "course's own, so it must match the description exactly.\n\nThe graph:\n{brief}\n\n"
        "The course's conventions: consumer surplus is pink, producer surplus is blue, a government amount (spending "
        "or receipts) is hatched green, welfare loss is yellow. Use the course's own letters and names exactly as "
        "given, Hebrew names in Hebrew.\n\n")
TODAY = re.search(r"\*\*Write a Graph spec\*\* into `[^`]+`\. (.*)", (US.parent / "unistudent" / "reference" / "study-pack.md").read_text("utf-8")).group(1)
ARMS = {
    "A": "Write a Graph spec; a tool draws it. " + TODAY + "\n\nAnswer with the Graph spec only, in one ```json block.",
    "B": ("Describe the graph as a JSON spec; a tool draws it. The spec format, as an example that shows every feature:\n\n"
          + draw_b.SPEC_DOC + "\n\nThe graph is conceptual: choose simple formulas with round numbers that give the slopes, "
          "order and positions described, so every crossing is exact. Place every named point by a crossing or on its curve; "
          "type coordinates only for a point on an axis or one that stands free. Answer with the spec only, in one ```json block."),
    "C0": ("Draw it as one standalone SVG picture. It must match the description exactly, be clean and easy to read, and "
           "look good in a study pack. Answer with the SVG only, in one ```svg block."),
    "C": ("Draw it as one standalone SVG picture. Rules:\n"
          "1. Exact geometry. The graph is conceptual, so choose a simple equation with round numbers for each curve, giving "
          "the slopes, order and positions described. Work out every named point from the equations and map it to pixels "
          "with one linear transform, so each point lies exactly on its curves and each area's corners are exactly those points.\n"
          "2. Draw areas first, then guide lines, then curves, then axes, then dots and names. Fill each area in the course's color.\n"
          "3. Readable: no name sits on a curve, on another name, or outside the picture. Curves about 3 px wide, guide lines thin and dashed.\n"
          "4. Portable: the picture is also shown outside a browser. Plain attributes only (fill=, stroke=): no CSS variables, "
          "no media queries, no scripts, no foreignObject, no external files or fonts. Use font-family=\"Arial, Helvetica, sans-serif\". "
          "Start with an opaque light background rectangle. Use viewBox=\"0 0 520 420\" with a width and a height.\n"
          "Answer with the SVG only, in one ```svg block."),
    "E": ("Produce the graph as two files in the current folder: graph.svg and graph.png (the same picture). Use whatever "
          "software you judge best for the job: you have a shell with python3 and uv (`uv run --with <package> python "
          "script.py` installs Python packages on the fly). Install nothing any other way. It must match the description "
          "exactly, be clean and easy to read, and look good in a study pack. Check your result before you finish. "
          "When done, answer with one line naming the software you used."),
}
FIXES = {"B2": "B", "D": "C"}
FIX = ("\n\nYou already answered with this:\n\n```\n{previous}\n```\n\nIt was drawn to the picture `preview.png` in the current "
       "folder. Open it with the Read tool and compare it with the description, as a strict reviewer. An automatic check "
       "(a heuristic: it can be wrong and it cannot see everything) reported:\n{problems}\n\nIf anything is wrong, misplaced, "
       "overlapping or cut off, answer with the corrected full answer in one fenced block. If nothing needs changing, "
       "answer with exactly: OK")
RUBRIC = ("You are checking a graph drawn for a university study pack against the course's description. Open `{code}.png` "
          "in the current folder with the Read tool and look at it carefully.\n\nThe description the graph must match:\n{brief}\n"
          "Course conventions: consumer surplus pink, producer surplus blue, a government amount hatched green, welfare loss yellow.\n\n"
          "Score strictly: a student will study from this. Answer with only a JSON object:\n"
          '{{"geometry": 0, "areas": 0, "labels": 0, "legibility": 0, "usable": false, "problems": ["..."]}}\n'
          "- geometry: 2 = every curve has the described slope, shape and order, and every named point sits exactly where "
          "described (on its curve or crossing); 1 = one small visible error; 0 = a point clearly off its curve, a wrong shift "
          "direction or a wrong order.\n"
          "- areas: 2 = every area in the description is filled, with the right corners and the course's color (2 when the "
          "description has no areas); 1 = one area wrong, missing or in the wrong color; 0 = most areas missing or wrong.\n"
          "- labels: 2 = every letter and name in the description is present, at the right place, and Hebrew reads correctly "
          "(not reversed, not empty boxes); 1 = one missing or misplaced; 0 = several missing, or Hebrew broken.\n"
          "- legibility: 2 = nothing overlaps or is cut off and it looks clean; 1 = one small overlap or cramped spot; "
          "0 = text on curves or on other text, cut-off parts, or a broken picture (black or blank).\n"
          "- usable: true only if a student could study from it without being misled.")


def ask(prompt, model, cwd, tools="", allow=None, budget="3"):
    cmd = ["claude", "-p", prompt, "--model", model, "--setting-sources", "project", "--strict-mcp-config",
           "--system-prompt", SYSTEM, "--tools", tools, "--output-format", "json", "--max-budget-usd", budget]
    if allow:
        cmd += ["--allowedTools", allow]
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=1500)
        reply = json.loads(done.stdout)
    except (ValueError, subprocess.TimeoutExpired) as error:
        reply = {"result": "", "error": str(error)[:300]}
    return {"text": reply.get("result") or "", "cost": reply.get("total_cost_usd", 0), "seconds": reply.get("duration_ms", 0) / 1000,
            "out_tokens": (reply.get("usage") or {}).get("output_tokens", 0), "turns": reply.get("num_turns", 0), "error": reply.get("error")}


def fenced(text):
    blocks = re.findall(r"```[a-z]*\n(.*?)```", text, re.S)
    raw = re.search(r"<svg.*</svg>", text, re.S)
    return (blocks[-1] if blocks else raw.group(0) if raw else text).strip()


def render(svg_text, png):
    import resvg_py
    png.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg_text, zoom=2)))


def build(arm, answer, folder):
    """Turn a model's answer into graph.png (and graph.svg). Returns an error text or None."""
    try:
        if arm in ("A",):
            (folder / "graph.json").write_text(answer, "utf-8")
            done = subprocess.run([sys.executable, str(US), "graph", str(folder / "graph.json"), "--force"], capture_output=True, text=True)
            return None if done.returncode == 0 else (done.stdout + done.stderr).strip()[-600:]
        svg = draw_b.draw(json.loads(answer)) if arm in ("B", "B2") else answer
        (folder / ("spec.json" if arm in ("B", "B2") else "answer.txt")).write_text(answer, "utf-8")
        (folder / "graph.svg").write_text(svg, "utf-8")
        render(svg, folder / "graph.png")
    except Exception as error:  # a model's answer can fail anywhere; the text goes back to the model
        return f"{type(error).__name__}: {error}"[:600]


def add(total, reply):
    for key in ("cost", "seconds", "out_tokens"):
        total[key] = total.get(key, 0) + reply[key]


def gen(out, case, name, arm):
    folder = out / case["id"] / name / arm
    if (folder / "run.json").exists():
        return
    folder.mkdir(parents=True, exist_ok=True)
    prompt, run = HEAD.format(brief=case["brief"]) + ARMS[arm], {"attempts": 1}
    if arm == "E":
        reply = ask(prompt, MODELS[name], folder, "Bash,Read,Write,Edit", "Bash Read Write Edit", "5")
        add(run, reply)
        run["software"], error = reply["text"][-300:], None if (folder / "graph.png").exists() else "no graph.png was produced"
    else:
        reply = ask(prompt, MODELS[name], folder)
        add(run, reply)
        error = build(arm, fenced(reply["text"]), folder)
        if error:  # the tool reported a problem: one more try with its message, as the rules allow
            run["attempts"], run["first_error"] = 2, error
            reply = ask(prompt + f"\n\nYour previous answer:\n```\n{fenced(reply['text'])}\n```\nfailed with: {error}\nAnswer again, corrected.",
                        MODELS[name], folder)
            add(run, reply)
            error = build(arm, fenced(reply["text"]), folder)
    run["error"] = error
    (folder / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), "utf-8")
    print("gen", case["id"], name, arm, "FAILED: " + error if error else "ok", flush=True)


def fix(out, case, name, arm):
    base, folder = out / case["id"] / name / FIXES[arm], out / case["id"] / name / arm
    if (folder / "run.json").exists() or not (base / "graph.png").exists():
        return
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(base / "graph.png", folder / "preview.png")
    previous = (base / ("spec.json" if arm == "B2" else "answer.txt")).read_text("utf-8")
    problems = checker.check((base / "graph.svg").read_text("utf-8"), case)
    run = dict(json.loads((base / "run.json").read_text("utf-8")), check_before=problems)
    prompt = HEAD.format(brief=case["brief"]) + ARMS[FIXES[arm]] + FIX.format(
        previous=previous, problems="\n".join("- " + p for p in problems) or "- no problems found")
    reply = ask(prompt, MODELS[name], folder, "Read")
    add(run, reply)
    run["changed"] = reply["text"].strip() != "OK"
    error = build(arm, fenced(reply["text"]) if run["changed"] else previous, folder)
    if error:  # a broken fix never replaces a working graph
        run["fix_error"], error = error, build(arm, previous, folder)
    run["error"] = error
    (folder / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), "utf-8")
    print("fix", case["id"], name, arm, "changed" if run["changed"] else "kept", flush=True)


def judge(out, case, folder):
    if (folder / "judge.json").exists() or not (folder / "graph.png").exists():
        return
    code = hashlib.sha256(str(folder.relative_to(out)).encode()).hexdigest()[:10]  # the judge never sees the arm or model
    room = out / "_judge"
    room.mkdir(exist_ok=True)
    shutil.copy(folder / "graph.png", room / f"{code}.png")
    reply = ask(RUBRIC.format(code=code, brief=case["brief"]), JUDGE, room, "Read")
    found = re.search(r"\{.*\}", reply["text"], re.S)
    try:
        (folder / "judge.json").write_text(json.dumps(json.loads(found.group(0)), ensure_ascii=False, indent=1), "utf-8")
    except (AttributeError, ValueError):
        print("judge unreadable", folder, reply["text"][:200], flush=True)


def report(out, cases):
    from PIL import Image, ImageDraw
    arms, rows = list(ARMS)[:2] + ["B2", "C0", "C", "D", "E"], []
    for case in cases:
        for name in MODELS:
            sheet = Image.new("RGB", (4 * 420, 2 * 360), "white")
            for i, arm in enumerate(arms):
                folder = out / case["id"] / name / arm
                run = json.loads((folder / "run.json").read_text("utf-8")) if (folder / "run.json").exists() else {}
                row = {"case": case["id"], "model": name, "arm": arm, "drawn": (folder / "graph.png").exists(),
                       **{k: run.get(k) for k in ("cost", "seconds", "out_tokens", "attempts", "changed", "software", "error")}}
                if (folder / "graph.svg").exists():
                    row["check"] = checker.check((folder / "graph.svg").read_text("utf-8"), case)
                if (folder / "judge.json").exists():
                    row["judge"] = json.loads((folder / "judge.json").read_text("utf-8"))
                    row["score"] = sum(row["judge"].get(k, 0) for k in ("geometry", "areas", "labels", "legibility"))
                rows.append(row)
                if row["drawn"]:
                    tile = Image.open(folder / "graph.png").convert("RGB")
                    tile.thumbnail((410, 330))
                    sheet.paste(tile, (i % 4 * 420 + 5, i // 4 * 360 + 26))
                ImageDraw.Draw(sheet).text((i % 4 * 420 + 8, i // 4 * 360 + 6), f"{arm}  score {row.get('score', '-')}", fill="black")
            sheet.save(out / f"sheet-{case['id']}-{name}.png")
    (out / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), "utf-8")
    mean = lambda values: round(sum(values) / len(values), 2) if values else None
    print(f"{'arm':4}{'model':8}{'drawn':>6}{'score/8':>9}{'usable':>8}{'check clean':>13}{'$ each':>8}{'sec':>6}{'out tok':>9}")
    for arm in arms:
        for name in list(MODELS) + ["all"]:
            mine = [r for r in rows if r["arm"] == arm and name in (r["model"], "all")]
            drawn, scored = [r for r in mine if r["drawn"]], [r for r in mine if "score" in r]
            checked = [r for r in mine if "check" in r]
            print(f"{arm:4}{name:8}{len(drawn):>4}/{len(mine)}{str(mean([r['score'] for r in scored])):>9}"
                  f"{sum(r['judge'].get('usable') is True for r in scored):>6}/{len(mine)}"
                  f"{(str(sum(not r['check'] for r in checked)) + '/' + str(len(checked))) if checked else '-':>13}"
                  f"{str(mean([r['cost'] for r in mine if r['cost']])):>8}{str(mean([r['seconds'] for r in mine if r['seconds']])):>6}"
                  f"{str(mean([r['out_tokens'] for r in mine if r['out_tokens']])):>9}")


def main():
    out = Path(sys.argv[1]).resolve()
    stages = sys.argv[2:] or ["gen", "fix", "judge", "report"]
    cases = json.loads((HERE / "cases.json").read_text("utf-8"))
    if not shutil.which("claude"):
        raise SystemExit("The `claude` CLI is needed to run this eval.")
    with ThreadPoolExecutor(8) as pool:
        jobs = {"gen": [(gen, out, c, m, a) for c in cases for m in MODELS for a in ARMS],
                "fix": [(fix, out, c, m, a) for c in cases for m in MODELS for a in FIXES],
                "judge": [(judge, out, c, out / c["id"] / m / a) for c in cases for m in MODELS for a in list(ARMS) + list(FIXES)]}
        for stage in stages:
            if stage == "report":
                report(out, cases)
            else:
                for result in [pool.submit(*job) for job in jobs[stage]]:
                    result.result()


if __name__ == "__main__":
    main()
