"""Checks every draft email must pass before it's written to the output file.

Cold email fails in predictable ways: too long, no clear ask, a made-up stat about the
prospect's company, or language that reads like a template. Each of those is checkable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
NUMBER_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s?%?")
MAX_WORDS = 120
TEMPLATE_OPENERS = ("i hope this email finds you well", "i hope you're doing well", "my name is",
                    "i wanted to reach out", "just following up")


@dataclass
class GuardReport:
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def as_feedback(self) -> str:
        return "\n".join(f"- {p}" for p in self.problems)


def _banned_words() -> list[str]:
    path = CONFIG_DIR / "banned_words.txt"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


MEETING_LENGTH_RE = re.compile(r"\b\d+[- ]?(?:min|minute|minutes|mins)\b", re.I)


def _numbers(text: str) -> set[str]:
    # "15-minute call" is an ask, not a claim about the prospect, so it's exempt.
    text = MEETING_LENGTH_RE.sub("", text)
    return {m.group().replace(",", "").replace(" ", "").replace("$", "") for m in NUMBER_RE.finditer(text)}


def split_email(text: str) -> tuple[str, str]:
    """Return (subject, body). Subject is the first 'Subject:' line."""
    match = re.search(r"^\s*subject:\s*(.+)$", text, re.I | re.M)
    if not match:
        return "", text.strip()
    body = (text[: match.start()] + text[match.end():]).strip()
    return match.group(1).strip(), body


def check_email(text: str, prospect: dict[str, str], product: str) -> GuardReport:
    report = GuardReport()
    subject, body = split_email(text)

    if not subject:
        report.problems.append("Start with a line 'Subject: ...'.")
    elif len(subject.split()) > 7:
        report.problems.append("Subject line is longer than 7 words.")

    words = len(body.split())
    if words > MAX_WORDS:
        report.problems.append(f"Body is {words} words. Keep it under {MAX_WORDS}.")
    if prospect.get("company") and prospect["company"].lower() not in body.lower():
        report.problems.append(f"Body never mentions {prospect['company']}. Make it specific to them.")
    if body.count("?") != 1:
        report.problems.append("End with exactly one question as the ask.")

    lines = [ln.strip().lower() for ln in body.splitlines() if ln.strip()]
    if lines and re.match(r"(hi|hello|hey|dear)\b", lines[0]) and len(lines[0].split()) <= 4:
        lines = lines[1:]  # skip the greeting, judge the real first sentence
    opener = lines[0] if lines else ""
    if any(o in opener for o in TEMPLATE_OPENERS):
        report.problems.append("Opening line sounds like a template. Open with something about them.")

    sources = " ".join([product, *prospect.values()])
    invented = _numbers(text) - _numbers(sources)
    if invented:
        report.problems.append(
            f"Numbers not in the prospect notes or product sheet: {', '.join(sorted(invented))}. Don't invent stats.")

    if "—" in text:
        report.problems.append("Remove em dashes.")
    if "!" in text:
        report.problems.append("No exclamation points.")
    banned = [w for w in _banned_words() if re.search(rf"\b{re.escape(w)}\b", text, re.I)]
    if banned:
        report.problems.append(f"Banned words used: {', '.join(banned)}.")
    return report
