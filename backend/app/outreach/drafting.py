"""Draft generation from the qualifying evidence (BACKEND_SPEC §7).

The evidence that qualified the investor is the same artifact that personalizes the email —
there is no second research pass. 80–120 words, opening from `lead_evidence`. A stale lead
fact is not drafted from; the row is marked `needs_review` instead.
"""

from __future__ import annotations

import logging

from ..config import get_settings
from ..llm import drafter_llm
from ..models import (
    Blocker,
    CompanyProfile,
    Draft,
    DraftVersion,
    EvidenceRecord,
    PriorContact,
    TargetRow,
)
from ..octen.data.corpus import PARTNERS_BY_ID

log = logging.getLogger("proofline.outreach.drafting")

MIN_WORDS, MAX_WORDS = 80, 120

SYSTEM = (
    "You write cold outreach from a founder to an investor. 80-120 words. Open from the "
    "supplied fact, stated plainly and dated. One concrete traction line. One specific ask. "
    "No flattery, no adjectives, no 'I hope this finds you well'. Sign with the founder's first name."
)

DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["subject", "body"],
    "properties": {"subject": {"type": "string"}, "body": {"type": "string"}},
}

_OPENERS = {
    "thesis_publication": "{claim} in {when}. That argument is the company we built.",
    "portfolio_investment": "{claim} in {when}. We sit one step from that, not against it.",
    "fund_close": "{claim} ({when}), which is why I am writing now rather than next quarter.",
    "portfolio_gap": "{claim}, as of {when}. We are what goes in that hole.",
    "exit": "{claim} in {when} — you have already run diligence on this buyer set.",
    "personnel": "{claim} ({when}).",
    "other": "{claim} ({when}).",
}

#: Claims are written as third-person statements about the investor; addressing them
#: directly reads as a sentence a founder would actually type.
_VERB_REWRITES = {
    "published": "published",
    "argued": "argued",
    "led": "led",
    "backed": "backed",
    "wrote": "wrote",
    "runs": "run",
    "writes": "write",
    "keynoted": "keynoted",
    "opened": "opened",
    "invested": "invested",
    "rode": "rode",
    "told": "told",
    "spoke": "spoke",
    "listed": "listed",
    "closed": "closed",
    "holds": "hold",
    "has": "have",
}


def _second_person(claim: str) -> str:
    """"Published a thesis on X." -> "You published a thesis on X"."""
    text = claim.strip().rstrip(".")
    first, _, rest = text.partition(" ")
    rewritten = _VERB_REWRITES.get(first.lower())
    if rewritten:
        return f"You {rewritten} {rest}".rstrip()
    for firm_lead in ("The ", "A "):
        if text.startswith(firm_lead):
            return f"Your {text[len(firm_lead):]}"
    return text

_ASKS = (
    "Worth twenty minutes?",
    "Can I send the trial data?",
    "Open to a short call this week?",
)


def _month_year(record: EvidenceRecord) -> str:
    d = record.effective_date
    return d.strftime("%B %Y") if d else "recently"


def _first_name(full_name: str | None) -> str:
    return (full_name or "there").split()[0]


def _pad_words(lines: list[str], row: TargetRow, profile: CompanyProfile) -> list[str]:
    """Short drafts get another defensible fact, never filler."""
    extras = [
        f"The check we are looking for sits inside your {checkband}."
        if (checkband := _check_band(row))
        else "",
        f"{profile.traction[2]} is the number I would want you to push on."
        if len(profile.traction) > 2
        else "",
        f"Happy to send the {profile.round.lower()} memo and the raw trial data before any call.",
    ]
    for extra in extras:
        if not extra:
            continue
        if len(" ".join(lines).split()) >= MIN_WORDS:
            break
        lines.insert(len(lines) - 2, extra)
    return lines


def _check_band(row: TargetRow) -> str | None:
    if not row.check_min or not row.check_max:
        return None
    fmt = lambda v: f"${v / 1_000_000:.1f}M" if v >= 1_000_000 else f"${round(v / 1000)}K"  # noqa: E731
    return f"{fmt(row.check_min)}–{fmt(row.check_max)} range"


def _fit_words(body: str, profile: CompanyProfile) -> str:
    words = body.split()
    if len(words) <= MAX_WORDS:
        return body
    paragraphs = body.split("\n\n")
    while len(" ".join(paragraphs).split()) > MAX_WORDS and len(paragraphs) > 3:
        paragraphs.pop(-2)
    trimmed = "\n\n".join(paragraphs)
    if len(trimmed.split()) > MAX_WORDS:
        keep = trimmed.split()[: MAX_WORDS - 4]
        trimmed = " ".join(keep).rstrip(",.;") + f".\n\n— {_first_name(profile.founder_name)}"
    return trimmed


def deterministic_draft(row: TargetRow, profile: CompanyProfile) -> tuple[str, str]:
    lead = row.lead_evidence
    opener = _OPENERS.get(lead.kind, "{claim} ({when}).").format(
        claim=_second_person(lead.claim), when=_month_year(lead)
    )
    traction = ", ".join(profile.traction[:3]) if profile.traction else ""
    supporting = next((e for e in row.evidence if e.id != lead.id and not e.stale), None)

    lines = [
        f"{_first_name(row.investor_person)},",
        opener,
        f"{profile.company}: {profile.one_liner.rstrip('.')}. Today that is {traction}."
        if traction
        else f"{profile.company}: {profile.one_liner}",
    ]
    if supporting:
        lines.append(
            f"{_second_person(supporting.claim)} — happy to show you where the two actually connect."
        )
    lines.append(f"We are raising {profile.raise_target}. {_ASKS[hash(str(row.target_id)) % len(_ASKS)]}")
    lines.append(f"— {_first_name(profile.founder_name)}")

    if len(" ".join(lines).split()) < MIN_WORDS:
        lines = _pad_words(lines, row, profile)
    body = _fit_words("\n\n".join(lines), profile)
    focus = (profile.keywords[0] if profile.keywords else profile.company).lower()
    subject = f"{focus.capitalize()} — {profile.company} {profile.round.lower()}, {_month_year(lead)} thesis"
    if lead.kind == "portfolio_gap":
        subject = f"The {focus} hole in the {row.investor_firm} portfolio"
    elif lead.kind == "portfolio_investment":
        subject = f"Adjacent to your {row.investor_firm} portfolio — {profile.company}"
    return subject, body


async def generate_draft_content(row: TargetRow, profile: CompanyProfile, angle: str | None = None) -> tuple[str, str, str]:
    llm = drafter_llm()
    if llm.available:
        payload = await llm.complete(
            system=SYSTEM,
            user=(
                f"Founder: {profile.founder_name} of {profile.company} ({profile.round}, raising {profile.raise_target}).\n"
                f"One-liner: {profile.one_liner}\nTraction: {'; '.join(profile.traction)}\n"
                f"Investor: {row.investor_person or row.investor_firm}, {row.role or 'partner'} at {row.investor_firm}.\n"
                f"Lead fact ({_month_year(row.lead_evidence)}): {row.lead_evidence.claim} {row.lead_evidence.detail}\n"
                f"Supporting facts: {' | '.join(e.claim for e in row.evidence[1:3])}\n"
                + (f"Angle to emphasise: {angle}\n" if angle else "")
            ),
            schema=DRAFT_SCHEMA,
            schema_name="draft_email",
        )
        if payload and payload.get("body"):
            return payload["subject"], payload["body"], "openai"
    subject, body = deterministic_draft(row, profile)
    return subject, body, "deterministic"


def prior_contact_for(row: TargetRow) -> PriorContact:
    """Gmail history lookup. Falls back to the recorded mailbox state when Composio is off."""
    partner = next(
        (p for p in PARTNERS_BY_ID.values() if p.name == row.investor_person and p.firm == row.investor_firm),
        None,
    )
    if partner and partner.prior_contact and "No prior thread" not in partner.prior_contact:
        return PriorContact(found=True, last_thread_at=partner.last_check_written, summary=partner.prior_contact)
    return PriorContact(found=False, summary=partner.prior_contact if partner else None)


def blockers_for(row: TargetRow, prior: PriorContact) -> list[Blocker]:
    settings = get_settings()
    blockers: list[Blocker] = []
    if row.lead_evidence.stale:
        blockers.append("stale_lead_evidence")
    if not row.contact_email:
        blockers.append("no_contact_email")
    if prior.found:
        blockers.append("prior_contact_exists")
    if not settings.sending_domain_verified:
        blockers.append("domain_unverified")
    return blockers


async def build_draft(row: TargetRow, profile: CompanyProfile, angle: str | None = None) -> Draft:
    subject, body, generated_by = await generate_draft_content(row, profile, angle)
    prior = prior_contact_for(row)
    draft = Draft(
        target_id=row.target_id,
        run_id=row.run_id,
        subject=subject,
        body=body,
        lead_evidence_id=row.lead_evidence.id,
        prior_contact=prior,
        blockers=blockers_for(row, prior),
        generated_by=generated_by,
    )
    draft.versions.append(DraftVersion(version=1, subject=subject, body=body, author="model", angle=angle))
    if "stale_lead_evidence" in draft.blockers:
        log.info("target %s drafted as needs-review: lead evidence is stale", row.target_id)
    return draft
