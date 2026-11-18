"""Check the published call log on your own machine, from a full git clone of it:

    git clone https://github.com/pdfinnigan/trade-analyst-calls && cd trade-analyst-calls
    python3 verify.py

Python 3.11+ and git, nothing to install. It checks that:

- every call's fingerprint matches its text and the fingerprint before it;
- every line of heads.txt names a fingerprint still in that chain, at the call count it gives;
- every earlier version of heads.txt in the repo's history is the start of today's, and so is
  the heads.txt this clone last passed (kept in .git/verified-heads), so no published
  fingerprint was ever taken back. Keep your clone: after a rewritten history, even one you
  reset to, the copy it last passed still holds the lines taken out;
- each night's random picks redraw from that night's published stock list and seed.

It prints what it checked and exits 1 on any problem. This file is copied into the public call
log as verify.py, so it imports nothing from the app."""

import hashlib
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

GENESIS = "0" * 64
SHEET_SIZE = 5
HEADS = "heads.txt"
VERIFIED = "verified-heads"  # in .git: the heads.txt this clone last passed


def fingerprint(body: str, previous: str) -> str:
    return hashlib.sha256(f"{previous}\n{body}".encode()).hexdigest()


def seed_for(day: str) -> int:
    return int(hashlib.sha256(f"call-sheet:{day}".encode()).hexdigest()[:16], 16)


def read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def parse_heads(text: str) -> list[tuple[str, str, int]]:
    """heads.txt lines: when, fingerprint, how many calls it covers. Raises ValueError."""
    heads = []
    for number, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if len(parts) != 3 or len(parts[1]) != 64 or not parts[2].isdigit():
            raise ValueError(f"{HEADS} line {number} is not 'time fingerprint count'")
        heads.append((parts[0], parts[1], int(parts[2])))
    return heads


def git(folder: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise ValueError(done.stderr.strip() or f"git {args[0]} failed")
    return done.stdout


def history_problems(folder: Path) -> list[str]:
    """Every committed version of heads.txt must be the start of the next one."""
    try:
        if git(folder, "rev-parse", "--is-shallow-repository").strip() == "true":
            return ["this is a shallow clone; clone the whole history to check it"]
        commits = git(folder, "log", "--reverse", "--format=%H", "--", HEADS).split()
        versions = [git(folder, "show", f"{commit}:{HEADS}") for commit in commits]
    except (OSError, ValueError) as error:
        return [f"can't read the git history ({error}); run this in a clone of the call log"]
    current = (folder / HEADS).read_text() if (folder / HEADS).exists() else ""
    remembered = folder / ".git" / VERIFIED
    if remembered.exists() and not current.startswith(remembered.read_text()):
        return [f"{HEADS} dropped lines this clone passed before; the history was rewritten"]
    if not commits:
        return []
    for commit, older, newer in zip(commits, versions, versions[1:] + [current], strict=True):
        if not newer.startswith(older):
            return [f"{HEADS} as of commit {commit[:12]} was later rewritten, not added to"]
    return []


def check(folder: Path, history: bool = True) -> list[str]:
    """Problems found, or an empty list when everything holds."""
    rows = read_lines(folder / "calls.jsonl")
    expected = GENESIS
    position = {GENESIS: 0}
    for count, row in enumerate(rows, 1):
        if row["previous"] != expected:
            return [f"call {row['id']}: the row before it was changed or removed"]
        if fingerprint(row["body"], row["previous"]) != row["fingerprint"]:
            return [f"call {row['id']}: its text does not match its fingerprint"]
        expected = row["fingerprint"]
        position[expected] = count
    heads = folder / HEADS
    try:
        published = parse_heads(heads.read_text() if heads.exists() else "")
    except ValueError as error:
        return [str(error)]
    for when, head, count in published:
        if position.get(head) != count:
            return [f"published fingerprint {head[:12]} ({when}) is not call {count} of the chain"]
    if history:
        problems = history_problems(folder)
        if problems:
            return problems

    sheets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        call = json.loads(row["body"])
        if call.get("source") == "sheet":
            sheets[call["day"]].append(call)
    pools = {item["day"]: item for item in read_lines(folder / "pools.jsonl")}
    problems = []
    for day, calls in sorted(sheets.items()):
        pool = pools.get(day)
        if pool is None:
            problems.append(f"{day}: no published stock list to redraw from")
            continue
        if hashlib.sha256(json.dumps(pool["tickers"]).encode()).hexdigest() != pool["pool"]:
            problems.append(f"{day}: the stock list does not match its fingerprint")
            continue
        if any(call["sheet_pool"] != pool["pool"] for call in calls):
            problems.append(f"{day}: the calls name a different stock list")
            continue
        seed = seed_for(day)
        if any(call["sheet_seed"] != seed for call in calls):
            problems.append(f"{day}: the calls carry a seed other than the day's")
            continue
        signals = {call["ticker"] for call in calls if call["pick"] == "signal"}
        if signals & set(pool["tickers"]):
            problems.append(f"{day}: signal picks {sorted(signals)} are also in the draw")
            continue
        wanted = min(SHEET_SIZE - len(signals), len(pool["tickers"]))
        drawn = set(random.Random(seed).sample(pool["tickers"], wanted))
        called = {call["ticker"] for call in calls if call["pick"] == "random"}
        if drawn != called:
            problems.append(f"{day}: random picks {sorted(called)}, redraw gives {sorted(drawn)}")
    return problems


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    problems = check(folder)
    for problem in problems:
        print("FAIL", problem)
    if problems:
        raise SystemExit(1)
    if (folder / ".git").is_dir() and (folder / HEADS).exists():
        (folder / ".git" / VERIFIED).write_text((folder / HEADS).read_text())
    count = len(read_lines(folder / "calls.jsonl"))
    print(f"OK: {count} calls, every published fingerprint and every sheet's draw checks out")


if __name__ == "__main__":
    main()
