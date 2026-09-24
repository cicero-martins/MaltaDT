"""Flag departures from the academic register required by CLAUDE.md.

The rule is stated in the project instructions but was applied inconsistently,
twice, which is the argument for making it checkable rather than remembered.
The patterns below are drawn from actual departures found in this repository
rather than from a general stylebook, so a hit is evidence of the failure mode
that has already occurred here.

The check is advisory. Some hits are legitimate, a quotation or a proper name
among them, and the script reports rather than enforces.

Usage:
    python check_register.py
    python check_register.py docs/one_file.md
    python check_register.py --quiet          # exit status only
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each entry is a label and a pattern. Ordered by how badly each reads in a
# document intended for supervisors and for a manuscript.
CHECKS: list[tuple[str, str]] = [
    ("first or second person",
     r"\b(we|our|ours|us|you|your|yours|I'm|I've|let's)\b"),
    ("em dash",
     r"—"),
    ("rhetorical aside",
     r"\b(uncomfortable|worked around|is thin|poor use|straightforward|"
     r"proper place|to their advantage|ground is open|read first|"
     r"no stakeholder|worth noting|it is worth|the trick|the catch|"
     r"the headline|the finding that matters|pays off|big deal)\b"),
    ("imperative or address to the reader",
     r"(^|\. )(Look to|Note that|Consider|Remember|Bear in mind|Keep in mind|"
     r"Ask |Check |Use |Read )"),
    ("meta-commentary on the document",
     r"\b(this section exists|as stated above|as mentioned|"
     r"as we (saw|noted)|in this document I)\b"),
    ("hyperbole",
     r"\b(dissolves|transformative|catastrophic|fatal|devastating|"
     r"enormous|huge|massive|dramatic(ally)?|stunning)\b"),
    ("judgemental section heading",
     r"^#{1,4} .*\b(why .* is (weak|wrong|bad)|what went wrong|the problem with|"
     r"what has already been done)\b"),
]

SKIP_DIRS = {".git", "data", "figures", "model", "__pycache__", ".ipynb_checkpoints"}
SUFFIXES = {".md", ".py"}

# An instruction file directs an agent and is legitimately imperative, so the
# imperative check is not applied to it. The register rules still are.
IMPERATIVE_EXEMPT = {"CLAUDE.md"}


def gather(targets: list[str]) -> list[Path]:
    if targets:
        return [Path(t) for t in targets]
    out: list[Path] = []
    for p in sorted(ROOT.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix in SUFFIXES and p.is_file() and p.name != Path(__file__).name:
            out.append(p)
    return out


def scan(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return hits
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # A markdown link target or a bare URL is not prose.
        prose = re.sub(r"\]\([^)]*\)|https?://\S+", "", line)
        for label, pattern in CHECKS:
            # In a heading the same word is usually a noun, as in "Use in the
            # present work", so the imperative check does not apply there.
            if label.startswith("imperative") and (
                    prose.lstrip().startswith("#") or path.name in IMPERATIVE_EXEMPT):
                continue
            flags = re.IGNORECASE | (re.MULTILINE if pattern.startswith("^") else 0)
            m = re.search(pattern, prose, flags)
            if m:
                frag = prose.strip()
                if len(frag) > 110:
                    start = max(0, m.start() - 45)
                    frag = "…" + frag[start:m.end() + 45].strip() + "…"
                hits.append((n, label, frag))
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", help="files to check, default all")
    ap.add_argument("--quiet", action="store_true", help="exit status only")
    args = ap.parse_args(argv)

    total = 0
    for path in gather(args.targets):
        hits = scan(path)
        if not hits:
            continue
        total += len(hits)
        if args.quiet:
            continue
        try:
            shown = path.relative_to(ROOT)
        except ValueError:
            shown = path
        print(f"\n{shown}")
        for n, label, frag in hits:
            print(f"  {n:>4}  {label:<38} {frag}")

    if not args.quiet:
        print(f"\n{total} advisory hit{'s' if total != 1 else ''}. "
              f"Some are legitimate; the check reports rather than enforces.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
