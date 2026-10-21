import csv
from pathlib import Path

from outreach.__main__ import load_prospects, write_outputs
from outreach.crew import draft_all, max_retries
from outreach.guards import check_email, split_email

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
PRODUCT = (EXAMPLES / "product.md").read_text()
PROSPECTS = load_prospects(EXAMPLES / "prospects.csv")
DANA = PROSPECTS[0]

GOOD = (
    "Subject: Shortening Northbeam's 9-day close\n"
    "Hi Dana,\n\nSaw your post about month-end taking 9 days at Northbeam Outdoor while you hire for AP. "
    "Ledgerline reads invoices straight from email and matches them to POs, so the new hire isn't keying "
    "them in by hand.\n\nWorth a 15-minute look before the role is filled?\n\nAlex"
)
INVENTED = GOOD.replace("9 days at Northbeam", "9 days at Northbeam, about 40% longer than peers,")
TEMPLATE = GOOD.replace("Hi Dana,\n\nSaw your post", "Hi Dana,\n\nI hope this email finds you well. Saw your post")
ANGLE = "Angle: slow close plus a new AP hire. Note: 'month-end close takes 9 days'."


def test_good_email_passes():
    report = check_email(GOOD, DANA, PRODUCT)
    assert report.ok, report.problems


def test_invented_stat_is_caught():
    assert any("40%" in p for p in check_email(INVENTED, DANA, PRODUCT).problems)


def test_template_opener_and_missing_subject_are_caught():
    problems = " ".join(check_email(TEMPLATE.split("\n", 1)[1], DANA, PRODUCT).problems)
    assert "Subject" in problems and "template" in problems


def test_split_email():
    subject, body = split_email(GOOD)
    assert subject.startswith("Shortening") and body.startswith("Hi Dana")


def test_crew_retries_then_passes(scripted):
    llm = scripted(ANGLE, INVENTED, ANGLE, GOOD)
    [draft] = draft_all([DANA], PRODUCT, "Alex", stub=llm)
    assert draft.report.ok and draft.attempts == 2
    assert "40%" in str(llm.prompts[-1])


def test_flagged_after_max_retries_and_outputs_written(scripted, tmp_path):
    llm = scripted(*([ANGLE, INVENTED] * (max_retries() + 1)))
    drafts = draft_all([DANA], PRODUCT, "Alex", stub=llm)
    write_outputs(drafts, tmp_path)
    rows = list(csv.DictReader((tmp_path / "drafts.csv").open()))
    assert rows[0]["status"] == "FLAGGED"
    assert "FLAGGED" in (tmp_path / "drafts.md").read_text()


def test_unquoted_comma_in_notes_gives_a_clear_error(tmp_path):
    bad = tmp_path / "p.csv"
    bad.write_text("name,title,company,notes\nDana,Controller,Northbeam,close takes 9 days, hiring AP\n")
    import pytest
    with pytest.raises(SystemExit, match="line 2"):
        load_prospects(bad)


def test_max_retries_is_read_at_call_time(monkeypatch):
    monkeypatch.setenv("OUTREACH_MAX_RETRIES", "0")
    assert max_retries() == 0
