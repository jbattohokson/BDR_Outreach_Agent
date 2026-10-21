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


def test_banned_word_forms_and_placeholders_are_caught():
    bad = GOOD.replace("so the new hire", "leveraging it at [Company], so the new hire")
    problems = " ".join(check_email(bad, DANA, PRODUCT).problems)
    assert "leverage" in problems and "[Company]" in problems

def test_unquoted_comma_in_notes_gives_a_clear_error(tmp_path):
    bad = tmp_path / "p.csv"
    bad.write_text("name,title,company,notes\nDana,Controller,Northbeam,close takes 9 days, hiring AP\n")
    import pytest
    with pytest.raises(SystemExit, match="line 2"):
        load_prospects(bad)


def test_max_retries_is_read_at_call_time(monkeypatch):
    monkeypatch.setenv("OUTREACH_MAX_RETRIES", "0")
    assert max_retries() == 0


# Audit 2026-10-21: drafts that passed every check before


def _draft(greeting, opener, extra=""):
    return (f"Subject: Faster close at Northbeam\n\n{greeting}\n\n{opener}\n"
            f"Northbeam Outdoor is hiring for AP, and the close takes 9 days.{extra} "
            "Ledgerline matches invoices to POs automatically.\nWorth a 15-minute call next week?\n\nBest,\nAlex")


def test_opener_variants_are_caught():
    for opener in ("I hope you’re doing well.", "I hope you are doing well.", "I'm reaching out about AP."):
        report = check_email(_draft("Hi Dana,", opener), PROSPECTS[0], PRODUCT)
        assert any("template" in p for p in report.problems), opener


def test_greeting_to_the_wrong_person_is_caught():
    report = check_email(_draft("Hi Priya,", "Saw your post about month-end."), PROSPECTS[0], PRODUCT)
    assert any("Priya" in p for p in report.problems)
    assert check_email(_draft("Hi Dana,", "Saw your post about month-end."), PROSPECTS[0], PRODUCT).ok


def test_spelled_out_stats_are_caught():
    extra = " Teams like yours cut close time in half and doubled throughput."
    problems = " ".join(check_email(_draft("Hi Dana,", "Saw your post.", extra), PROSPECTS[0], PRODUCT).problems)
    assert "in half" in problems and "doubled" in problems


def test_implied_customer_proof_is_caught_unless_the_product_sheet_backs_it():
    hint = GOOD.replace("Worth a 15-minute look", "Could I share how we've helped other companies? Worth a 15-minute look")
    hint = hint.replace("?\n\nAlex", ".\n\nAlex").replace("companies?", "companies,")
    assert any("Implies customer results" in p for p in check_email(hint, DANA, PRODUCT).problems)
    backed = PRODUCT + "\nCustomers include three regional retailers (case studies on request).\n"
    assert not any("Implies" in p for p in check_email(hint, DANA, backed).problems)
