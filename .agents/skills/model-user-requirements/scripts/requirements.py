"""Look up model requirements and check reconciliation against the Git index."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(".agents/skills/model-user-requirements")
CATALOG = SKILL / "catalog"
STATES = ("active", "candidate", "evidence", "superseded")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def git(*args):
    return subprocess.check_output(["git", *args])


def catalog(staged=False):
    paths = CATALOG.rglob("*.json")
    if staged:
        indexed = git("ls-files", "-z", "--", str(CATALOG)).split(b"\0")
        paths = (Path(path.decode()) for path in indexed if path)
    records = {}
    for path in sorted(paths):
        if path.suffix != ".json":
            continue
        scope = path.relative_to(CATALOG).with_suffix("").as_posix()
        items = json.loads(git("show", f":{path}") if staged else path.read_bytes())
        if not isinstance(items, list) or not all(SLUG.fullmatch(s) for s in scope.split("/")):
            raise ValueError(f"Invalid list or scope in {path}")
        for item in items:
            key = item["id"]
            if not SLUG.fullmatch(key) or key in records or item["status"] not in STATES:
                raise ValueError(f"Invalid or duplicate record {key} in {path}")
            if not isinstance(item["text"], str) or not item["text"].strip():
                raise ValueError(f"Missing requirement text for {key}")
            if set(item) - {"id", "text", "status", "supersedes"}:
                raise ValueError(f"Unexpected field in {key}")
            if not isinstance(item.get("supersedes", []), list):
                raise ValueError(f"Invalid supersession list for {key}")
            records[key] = dict(item, scope=scope)
    if not records:
        raise ValueError("No model requirements found. Run from the repository root.")
    def visit(key, visiting):
        if key in visiting:
            raise ValueError(f"Supersession cycle at {key}")
        for prior in records[key].get("supersedes", []):
            if prior not in records or records[prior]["status"] != "superseded":
                raise ValueError(f"{key} supersedes missing or live record {prior}")
            visit(prior, visiting | {key})
    for key in records:
        visit(key, set())
    return records


def lookup(records, scope, history):
    known = {r["scope"] for r in records.values()}
    if not any(s == scope or s.startswith(scope + "/") for s in known):
        raise ValueError(f"Unknown scope {scope}. Available: {', '.join(sorted(known))}")
    for state in STATES:
        if state != "active" and not history:
            continue
        for rec in records.values():
            owner = rec["scope"]
            if rec["status"] == state and (owner == "all" or owner == scope or scope.startswith(owner + "/") or owner.startswith(scope + "/")):
                print(f"{state:10} {owner} / {rec['id']} — {rec['text']}")


def family(path):
    if path.endswith(".md"):
        return None
    if path.startswith(("magic-wand/hardware/carbon-rod-holders", "docs/assembly/", "magic-wand/scripts/assembly_publish.", "magic-wand/scripts/serve_assembly.")):
        return "carbon-rod"
    if path.startswith(("magic-wand/hardware/printed-loop-wand/", "magic-wand-3d-models/")):
        return "printed-loop"
    if path.startswith("magic-wand/hardware/assembly-blueprint/"):
        return "blueprint"
    if path.startswith("magic-wand/") and Path(path).suffix.lower() in {".step", ".stp", ".stl", ".3mf", ".scad", ".fcstd", ".glb"}:
        return "all"
    return None


def staged_changes(base):
    raw = git("diff", "--cached", "--raw", "--no-abbrev", "--no-renames", "-z", *base, "--").split(b"\0")[:-1]
    return [(meta, path) for meta, path in zip(raw[::2], raw[1::2]) if family(path.decode())]


def digest(changes, records, decision):
    h = hashlib.sha256()
    for meta, path in changes:
        h.update(meta + b"\0" + path + b"\0")
    h.update(json.dumps(records, sort_keys=True).encode())
    h.update(decision.encode())
    return h.hexdigest()


def receipt(changes, records, decision):
    ids = decision.split(",")
    families = {family(path.decode()) for _, path in changes} | {"all"}
    if decision != "no-new" and any(key not in records or records[key]["status"] == "superseded"
                                     or records[key]["scope"].split("/")[0] not in families for key in ids):
        raise ValueError("Name the captured or existing applicable record IDs, or use no-new.")
    return f"Model-requirements: {decision} {digest(changes, records, decision)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    show = sub.add_parser("show")
    show.add_argument("scope")
    show.add_argument("--history", action="store_true")
    sub.add_parser("validate")
    review = sub.add_parser("reconcile")
    review.add_argument("decision", help="IDs separated by commas, or no-new")
    check = sub.add_parser("check-message")
    check.add_argument("message", type=Path)
    for staged in (review, check):
        staged.add_argument("--base", help="Parent commit of a separate publication index (defaults to HEAD)")
    args = parser.parse_args()
    if args.cmd in {"show", "validate"}:
        records = catalog()
        if args.cmd == "show":
            lookup(records, args.scope, args.history)
        else:
            print(f"{len(records)} valid model records")
        return
    base = [git("rev-parse", "--verify", "--end-of-options", args.base + "^{commit}").decode().strip()] if args.base else []
    changes = staged_changes(base)
    if not changes:
        if args.cmd == "reconcile":
            raise ValueError("Stage the intended model change before reconciliation.")
        if git("diff", "--cached", "--name-only", *base, "--", str(CATALOG)):
            catalog(staged=True)
        return
    records = catalog(staged=True)
    if args.cmd == "reconcile":
        for name in sorted({family(path.decode()) for _, path in changes}):
            lookup(records, name, False)
        print(receipt(changes, records, args.decision))
        return
    lines = [s for s in args.message.read_text().splitlines() if s.startswith("Model-requirements: ")]
    if len(lines) == 1 and len(lines[0].split()) == 3:
        if lines[0] == receipt(changes, records, lines[0].split()[1]):
            return
    raise ValueError("Staged model changes need a current Model-requirements trailer. Run the model-user-requirements skill's reconcile command.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
