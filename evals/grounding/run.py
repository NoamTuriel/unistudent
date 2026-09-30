#!/usr/bin/env python3
"""Grounding eval (seam 3): ask Claude real questions inside a fixture course folder, grade the answers.

Needs the `claude` CLI on PATH and runs the model, so it is a periodic eval, not a unit test.
Usage: python3 evals/grounding/run.py [--keep]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
US = HERE.parents[1] / "plugins" / "unistudent" / "scripts" / "us.py"
PROMPT_SUFFIX = ("\n\nWrite your answer as Markdown. Cite Wiki pages with Markdown links relative to "
                 "this folder (e.g. wiki/sources/...).")


def us(*args, env):
    result = subprocess.run([sys.executable, str(US), *map(str, args), "--json"],
                            capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise SystemExit(result.stdout + result.stderr)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep the temp folder for inspection")
    args = parser.parse_args()
    if not shutil.which("claude"):
        raise SystemExit("The `claude` CLI is needed to run this eval.")

    tmp = Path(tempfile.mkdtemp(prefix="unistudent-eval-"))
    env = dict(os.environ, UNISTUDENT_HOME=str(tmp / "home"))
    macro, micro = tmp / "Macro", tmp / "Micro"
    us("setup", micro, "--name", "Micro", "--language", "en", "--import", HERE / "fixture" / "micro",
       "--tier", "official", env=env)
    us("wiki", "build", "--course", micro, env=env)
    us("setup", macro, "--name", "Macro", "--language", "en", "--import", HERE / "fixture" / "macro",
       "--tier", "official", env=env)
    us("wiki", "build", "--course", macro, env=env)

    results = []
    for case in json.loads((HERE / "cases.json").read_text("utf-8")):
        answer = subprocess.run(["claude", "-p", case["question"] + PROMPT_SUFFIX,
                                 "--allowedTools", "Read,Grep,Glob"],
                                cwd=macro, capture_output=True, text=True, env=env).stdout
        answer_file = macro / f"answer-{case['id']}.md"  # links are relative to the course folder
        answer_file.write_text(answer, "utf-8")
        case_file = tmp / f"{case['id']}.json"
        case_file.write_text(json.dumps(case), "utf-8")
        result = us("eval-grade", "--course", macro, case_file, answer_file, env=env)
        results.append(result)
        print(("PASS " if result["passed"] else "FAIL ") + case["id"], *result["failures"], sep="\n  - ")

    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed. Answers in {macro}" if args.keep else
          f"\n{passed}/{len(results)} passed.")
    if not args.keep:
        shutil.rmtree(tmp)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
