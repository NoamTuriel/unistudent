"""MCP server (stdio, JSON-RPC 2.0): every command line command becomes a tool, every skill a prompt.

Tools are generated from the command line parser, so the CLI stays the single source of truth:
`us wiki build --force` is the tool `wiki_build` with {"force": true}. Standard library only.
Works in any MCP client: Claude Desktop/Code, Cursor, VS Code, Codex, Gemini CLI.
"""
import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

from . import __version__, cli

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
HIDDEN_COMMANDS = {"eval-grade", "manifest"}  # developer tools, and output too large for a chat
# Commands with several actions share one parser; these are the arguments each action uses.
ACTION_ARGS = {
    ("courses", "list"): [], ("courses", "current"): [], ("courses", "switch"): ["target"],
    ("prefs", "show"): ["course"], ("prefs", "add"): ["course", "scope", "text"],
    ("wiki", "check"): ["course"], ("wiki", "build"): ["course", "force"],
    ("recordings", "list"): ["course", "unit"], ("recordings", "estimate"): ["course", "unit"],
    ("recordings", "benchmark"): ["course", "paths"],
    ("recordings", "transcribe"): ["course", "paths", "background"],
    ("recordings", "fetch"): ["course", "paths", "audio_only"],
}
REQUIRED = {("courses", "switch"): ["target"], ("prefs", "add"): ["text"],
            ("recordings", "benchmark"): ["paths"], ("recordings", "transcribe"): ["paths"],
            ("recordings", "fetch"): ["paths"]}
SKILL_DIRS = [Path(__file__).resolve().parent / "skills"]
# In a repo checkout, subject and university plugins' skills are prompts too.
_REPO_PLUGINS = Path(__file__).resolve().parents[3]
if (_REPO_PLUGINS / "unistudent").is_dir():
    SKILL_DIRS += sorted(p / "skills" for p in _REPO_PLUGINS.iterdir() if (p / "skills").is_dir())


def _subparsers(parser):
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return action.choices, {c.dest: c.help for c in action._choices_actions}


def _arg_schema(action):
    if isinstance(action, argparse._StoreTrueAction):
        schema = {"type": "boolean"}
    elif action.nargs in ("*", "+"):
        schema = {"type": "array", "items": {"type": "string"}}
    else:
        schema = {"type": "string"}
        if action.choices:
            schema["enum"] = list(action.choices)
    if action.help:
        schema["description"] = action.help
    return schema


def _arg_name(action):
    if action.option_strings:
        return action.option_strings[-1].lstrip("-").replace("-", "_")
    return action.dest


def build_tools():
    """[(tool dict, command words, parser)] generated from the CLI."""
    commands, helps = _subparsers(cli.build_parser())
    tools = []
    for command, sub in commands.items():
        if command in HIDDEN_COMMANDS:
            continue
        args = [a for a in sub._actions if not isinstance(a, argparse._HelpAction) and a.dest != "json"]
        verb = next((a for a in args if a.dest == "action" and a.choices), None)
        for choice in (list(verb.choices) if verb else [None]):
            props, required = {}, []
            only = ACTION_ARGS.get((command, choice))
            for a in args:
                if a is verb or (only is not None and _arg_name(a) not in only):
                    continue
                props[_arg_name(a)] = _arg_schema(a)
                if (not a.option_strings and a.nargs not in ("*", "?")) or getattr(a, "required", False):
                    required.append(_arg_name(a))
            required += [r for r in REQUIRED.get((command, choice), []) if r not in required]
            name = "_".join(w.replace("-", "_") for w in [command] + ([choice] if choice else []))
            description = helps.get(command) or command
            if choice:
                description = f"{description} ({choice})"
            tools.append(({"name": name, "description": description,
                           "inputSchema": {"type": "object", "properties": props, "required": required}},
                          [command] + ([choice] if choice else []), sub, verb))
    return tools


def _argv(words, sub, verb, arguments):
    argv = list(words)
    for a in sub._actions:
        if isinstance(a, argparse._HelpAction) or a.dest == "json" or a is verb:
            continue
        value = arguments.get(_arg_name(a))
        if value is None or value is False:
            continue
        values = value if isinstance(value, list) else [value]
        if not a.option_strings:
            argv += [str(v) for v in values]
        elif isinstance(a, argparse._StoreTrueAction):
            argv.append(a.option_strings[-1])
        elif isinstance(value, dict):  # e.g. describe: {"file": "origin"}
            argv += [a.option_strings[-1]] + [f"{k}={v}" for k, v in value.items()]
        else:
            argv += [a.option_strings[-1]] + [str(v) for v in values]
    return argv + ["--json"]


def call_tool(tools, name, arguments):
    match = next((t for t in tools if t[0]["name"] == name), None)
    if match is None:
        return None
    _, words, sub, verb = match
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(_argv(words, sub, verb, arguments or {}))
    except SystemExit as exit_:  # argparse rejected the arguments
        code = exit_.code or 2
    except Exception as error:  # never let one failing tool take the server down
        code = 1
        err.write(f"{type(error).__name__}: {error}")
    text = out.getvalue().strip() or err.getvalue().strip() or "{}"
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "error" in data:
            text, code = data["error"], code or 1
    except ValueError:
        pass
    return {"content": [{"type": "text", "text": text}], "isError": bool(code)}


def _skills():
    found = {}
    for folder in SKILL_DIRS:
        for skill in sorted(folder.glob("*/SKILL.md")):
            text = skill.read_text("utf-8")
            meta = dict(re.findall(r"(?m)^(name|description):\s*\"?(.*?)\"?\s*$",
                                   text.split("---")[1] if text.startswith("---") else ""))
            body = re.sub(r"\A---.*?---\s*", "", text, flags=re.S)
            body = body.replace("<this skill's base directory>", str(skill.parent))
            found.setdefault(meta.get("name", skill.parent.name),
                             {"description": meta.get("description", ""), "body": body})
    return found


def handle(message, tools):
    if not isinstance(message, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    method, params, id_ = message.get("method"), message.get("params") or {}, message.get("id")
    if id_ is None:
        return None  # notifications need no answer
    if method == "initialize":
        asked = params.get("protocolVersion")
        result = {"protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  "capabilities": {"tools": {}, "prompts": {}},
                  "serverInfo": {"name": "unistudent", "version": __version__},
                  "instructions": "UniStudent: per-course Wiki, grounded answers and study packs. "
                                  "Start with the prompt 'course-help', or 'course-setup' for a new course."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [t[0] for t in tools]}
    elif method == "tools/call":
        result = call_tool(tools, params.get("name"), params.get("arguments"))
        if result is None:
            return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32602, "message": f"Unknown tool {params.get('name')}"}}
    elif method == "prompts/list":
        result = {"prompts": [{"name": n, "description": s["description"]} for n, s in _skills().items()]}
    elif method == "prompts/get":
        skill = _skills().get(params.get("name"))
        if skill is None:
            return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32602, "message": "Unknown prompt"}}
        result = {"description": skill["description"],
                  "messages": [{"role": "user", "content": {"type": "text", "text": skill["body"]}}]}
    else:
        return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": f"Unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def main():
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    tools = build_tools()
    protocol_out = sys.stdout
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            message = None
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            try:
                reply = handle(message, tools)
            except Exception as error:
                reply = {"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None,
                         "error": {"code": -32603, "message": f"{type(error).__name__}: {error}"}}
        if reply is not None:
            protocol_out.write(json.dumps(reply, ensure_ascii=False) + "\n")
            protocol_out.flush()


if __name__ == "__main__":
    main()
