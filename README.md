# BDR Outreach Agent

Drafts a first-touch cold email for every prospect in a CSV, then fact-checks each draft in plain Python before it's saved. If the model invents a stat about the prospect, runs long, skips the ask or opens with "I hope this email finds you well", the draft goes back with the exact problem listed. After two failed retries it's saved marked **FLAGGED**. Nothing is ever sent: the output is a review file for a human rep.

Built with [CrewAI](https://docs.crewai.com). Runs free on a local model through Ollama. Switching to Claude is one line in `.env`.

**Business question:** can a small, free model write outbound emails a rep would actually send, as long as code catches the predictable failures?

## How it works

```
Account Researcher ──> Outbound Email Writer ──> guards ──┬─ pass ──> output/drafts.md + drafts.csv
  (one angle from          (Subject + body          │     └─ fail ──> retry with feedback (max 2)
   the prospect notes)      under 120 words)        └─ still failing ──> saved as FLAGGED
```

| Check | What it catches |
|---|---|
| Invented numbers | Any figure that isn't in the prospect notes or product sheet ("15-minute call" is allowed) |
| Personalization | The body never names the prospect's company |
| One ask | The body must end with exactly one question |
| Template opener | "My name is...", "I wanted to reach out...", and similar first lines (the greeting is skipped) |
| Length | Subject over 7 words, body over 120 words |
| Style | Em dashes, exclamation points, banned words (`config/banned_words.txt`) |

## Setup

```bash
git clone https://github.com/jbattohokson/BDR_Outreach_Agent && cd BDR_Outreach_Agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

ollama pull qwen2.5:7b   # free local model, about 4.7 GB
```

## Use it

```bash
python -m outreach --prospects examples/prospects.csv --product examples/product.md --sender "Alex"
```

The prospects CSV needs `name,title,company,notes` columns. The notes are the only research the agents see, so put real, checkable facts there (a job post, a LinkedIn post, an expansion announcement). Output goes to `output/drafts.md` (for reading) and `output/drafts.csv` (status, attempts, subject, body, problems).

## Example inputs are fictional

`examples/product.md` ("Ledgerline", an accounts payable tool) and `examples/prospects.csv` (two people at made-up companies) are invented for this demo. No real person's name or contact details are in this repo, and `.gitignore` blocks any other `prospects*.csv` so a real list can't be committed by accident.

## Switching models

Set `LLM_MODEL` in `.env`:

| Value | Cost | Notes |
|---|---|---|
| `ollama/qwen2.5:7b` | Free | Default |
| `ollama/llama3.1:8b` | Free | Alternative local model |
| `anthropic/claude-sonnet-5-5` | Paid | Run `pip install "crewai[anthropic]"` and set `ANTHROPIC_API_KEY` |

The guards stay the same when the model changes.

## Testing status (2026-10-20)

- `pytest`: 6 passed, run 3 times with identical results. A scripted fake model stands in for the LLM, so the tests run offline. They cover a clean email passing, an invented stat being caught, a template opener and missing subject being caught, subject/body splitting, a retry that fixes the draft, and the FLAGGED fallback with both output files written.
- Not tested here: live runs against Ollama or Claude. The tests prove the guards and retry loop, not how persuasive the emails are. Reply rates would need a real send and a comparison group.

## Limits

- The number check compares text, so a stat restated in a different form ("nine days" for "9 days") isn't caught.
- The agents don't browse the web. A draft is only as specific as the notes column.

## License

MIT (see `LICENSE`).
