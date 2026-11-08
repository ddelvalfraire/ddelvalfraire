"""Pinned, credential-free project checks; Python standard library only."""
import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "psi": ("postscript-interpreter", "e949359257e49c6ac54d2c33076bd9b21ee44c97"),
    "Quanta": ("Quanta", "2e0076e4ca40224f21c388ac471b1d92507c9519"),
}


def run(command, cwd, timeout=600):
    start = time.monotonic()
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(command, cwd=cwd, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                code = 124
            log.seek(0)
            output = log.read().decode("utf-8", errors="replace")
    except OSError as error:
        code, output = 127, str(error)
    return dict(command=shlex.join(command), time=stamp,
                seconds=round(time.monotonic() - start, 3), exit=code, output=output)


def render(results):
    sections = []
    for name, result in results.items():
        passed = bool(result["steps"]) and all(s["exit"] == 0 for s in result["steps"])
        sections.append(f"#### {name}: {'PASS' if passed else 'FAIL'}\n\n"
                        f"Revision: `{result['revision']}`\n")
        for step in result["steps"]:
            # HTML escaping also prevents output from closing the details element.
            preview = f"$ {step['command']}\n" + "\n".join(step['output'].splitlines()[-12:])[-1600:]
            sections.append(f"\n<details><summary>{html.escape(step['time'])}: "
                            f"exit {step['exit']}, {step['seconds']}s</summary>\n\n"
                            f"<pre>{html.escape(preview)}</pre>\n</details>\n")
    return "\n".join(sections)


def publish(results):
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/latest.json").write_text(json.dumps(results, indent=2) + "\n")
    template = (ROOT / "README.template.md").read_text()
    (ROOT / "README.md").write_text(template.replace("<!-- RESULTS -->", render(results)))


def check(name, directory):
    repo, revision = PINS[name]
    result = dict(revision=revision, steps=[])

    def attempt(args, cwd=directory):
        step = run(args, cwd)
        result["steps"].append(step)
        return step["exit"] == 0

    if not attempt(["git", "init", "-q"]):
        return result
    if not attempt(["git", "fetch", "--depth=1",
                    f"https://github.com/ddelvalfraire/{repo}.git", revision]):
        return result
    if not attempt(["git", "checkout", "--detach", "FETCH_HEAD"]):
        return result
    if name == "psi":
        attempt(["bun", "--version"])
        if not attempt(["bun", "install", "--frozen-lockfile", "--ignore-scripts"]):
            return result
        attempt(["bun", "test"], directory / "packages/interpreter")
        adapter = directory / "packages/interpreter/profile-render.ts"
        adapter.write_text('import { Interpreter } from "./src/index.ts";\n'
                           'const engine = new Interpreter();\n'
                           'engine.onOutput = s => process.stdout.write(s);\n'
                           'const result = engine.eval(await Bun.file(process.argv[2]).text());\n'
                           'if (result.isErr()) { console.error(result.error); process.exit(1); }\n')
        step = run(["bun", "run", str(adapter), str(ROOT / "banner.ps")], directory)
        result["steps"].append(step)
        if step["exit"] == 0:
            try:
                svg = ET.fromstring(step["output"])
                assert svg.tag == "{http://www.w3.org/2000/svg}svg"
                (ROOT / "assets").mkdir(exist_ok=True)
                (ROOT / "assets/banner.svg").write_text(step["output"])
            except (ET.ParseError, AssertionError) as error:
                step.update(exit=1, output=step["output"] + f"\nInvalid SVG: {error}")
    else:
        attempt(["cargo", "--version"])
        attempt(["rustc", "--version"])
        attempt(["cargo", "test", "--locked", "-p", "quanta-core-rs"], directory / "rust")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pending", action="store_true")
    args = parser.parse_args()
    results = {name: dict(revision=pin[1], steps=[dict(
        command="nightly check", time=dt.datetime.now(dt.timezone.utc).isoformat(),
        seconds=0, exit=125, output="Attempt started; no completed result yet.")])
        for name, pin in PINS.items()}
    publish(results)
    if args.pending:
        return
    for name in PINS:
        with tempfile.TemporaryDirectory(prefix="profile-check-") as directory:
            results[name] = check(name, Path(directory))
        publish(results)
    raise SystemExit(int(any(s["exit"] for r in results.values() for s in r["steps"])))


if __name__ == "__main__":
    main()
