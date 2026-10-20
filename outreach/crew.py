"""Research angle -> draft email -> guards -> retry. One crew run per prospect."""
from __future__ import annotations

import os
from dataclasses import dataclass

from crewai import Agent, BaseLLM, Crew, Process, Task

from outreach.guards import GuardReport, check_email
from outreach.llm import get_llm

MAX_RETRIES = int(os.getenv("OUTREACH_MAX_RETRIES", "2"))
RULES = (
    "Rules: Use only facts from the prospect notes and product sheet. Never invent numbers, "
    "customers or news about the prospect. No em dashes, no exclamation points, no buzzwords. "
    "Write like a peer, not a vendor."
)


@dataclass
class Draft:
    prospect: dict[str, str]
    text: str
    report: GuardReport
    attempts: int


def _agent(role: str, goal: str, backstory: str, llm: BaseLLM) -> Agent:
    return Agent(role=role, goal=goal, backstory=f"{backstory}\n\n{RULES}", llm=llm,
                 allow_delegation=False, verbose=os.getenv("CREW_VERBOSE") == "1")


def build_crew(llm: BaseLLM, feedback: str = "") -> Crew:
    researcher = _agent(
        "Account Researcher",
        "Find the one problem this prospect most likely has that the product solves",
        "You prep reps before outreach. You work only from the notes you're given and say "
        "plainly when the notes are thin.", llm)
    writer = _agent(
        "Outbound Email Writer",
        "Write a short first-touch email that earns a reply",
        "You write cold emails that read like a note from a person who did their homework.", llm)

    research = Task(
        description=(
            "Prospect: {name}, {title} at {company}.\nNotes: {notes}\n\nProduct sheet:\n{product}\n\n"
            "Give the single best angle: the prospect's likely problem, the product capability that "
            "fits it, and the exact note it's based on."),
        expected_output="One angle with the supporting note quoted.", agent=researcher)
    retry = ("" if not feedback else
             f"\n\nYour last draft was rejected. Fix every item and change nothing else:\n{feedback}")
    write = Task(
        description=(
            "Write the email to {name} from {sender}. Format:\nSubject: <7 words or fewer>\n<body>\n\n"
            "Body under 120 words. Open with something specific to {company}. Connect it to one product "
            "capability. End with exactly one low-pressure question." + retry),
        expected_output="A 'Subject:' line, then the email body.", agent=writer, context=[research])
    return Crew(agents=[researcher, writer], tasks=[research, write], process=Process.sequential, verbose=False)


def draft_email(prospect: dict[str, str], product: str, sender: str, llm: BaseLLM) -> Draft:
    inputs = {**{k: prospect.get(k, "") for k in ("name", "title", "company", "notes")},
              "product": product, "sender": sender}
    feedback, text, report = "", "", GuardReport(["Model never ran."])
    for attempt in range(1, MAX_RETRIES + 2):
        text = str(build_crew(llm, feedback).kickoff(inputs=inputs).raw).strip()
        report = check_email(text, prospect, product)
        if report.ok:
            return Draft(prospect, text, report, attempt)
        feedback = report.as_feedback()
    return Draft(prospect, text, report, MAX_RETRIES + 1)


def draft_all(prospects: list[dict[str, str]], product: str, sender: str,
              stub: BaseLLM | None = None) -> list[Draft]:
    llm = get_llm(stub)
    return [draft_email(p, product, sender, llm) for p in prospects]
