"""Draft first-touch emails for every prospect in a CSV. Nothing is ever sent.

    python -m outreach --prospects examples/prospects.csv --product examples/product.md --sender "Alex"
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from dotenv import load_dotenv

from outreach.crew import Draft, draft_all
from outreach.guards import split_email
from outreach.llm import MissingProviderError

REQUIRED_COLUMNS = {"name", "title", "company", "notes"}


def load_prospects(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        sys.exit(f"File not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            sys.exit(f"{path} is missing columns: {', '.join(sorted(missing))}")
        rows = []
        for line_no, row in enumerate(reader, start=2):
            if None in row:  # DictReader puts extra fields under None, e.g. an unquoted comma in notes
                sys.exit(f"{path} line {line_no} has more fields than headers. Quote values that contain commas.")
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return [r for r in rows if r.get("name")]


def write_outputs(drafts: list[Draft], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "drafts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "company", "status", "attempts", "subject", "body", "problems"])
        for d in drafts:
            subject, body = split_email(d.text)
            writer.writerow([d.prospect["name"], d.prospect["company"], "ready" if d.report.ok else "FLAGGED",
                             d.attempts, subject, body, d.report.as_feedback()])
    blocks = []
    for d in drafts:
        flag = "" if d.report.ok else f"\n\n**FLAGGED, review before sending:**\n{d.report.as_feedback()}"
        blocks.append(f"## {d.prospect['name']} ({d.prospect['company']})\n\n{d.text}{flag}")
    (out_dir / "drafts.md").write_text("\n\n---\n\n".join(blocks) + "\n", encoding="utf-8")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="outreach", description="Fact-checked cold email drafts.")
    parser.add_argument("--prospects", required=True, help="CSV with name,title,company,notes")
    parser.add_argument("--product", required=True, help="Markdown or text product sheet")
    parser.add_argument("--sender", required=True, help="Your first name, used to sign the email")
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    prospects = load_prospects(Path(args.prospects))
    product_path = Path(args.product)
    if not product_path.is_file():
        sys.exit(f"File not found: {product_path}")
    try:
        drafts = draft_all(prospects, product_path.read_text(encoding="utf-8"), args.sender)
    except MissingProviderError as exc:
        sys.exit(str(exc))
    write_outputs(drafts, Path(args.out))
    ready = sum(d.report.ok for d in drafts)
    print(f"{ready}/{len(drafts)} drafts ready, {len(drafts) - ready} flagged. See {args.out}/drafts.md")


if __name__ == "__main__":
    main()
