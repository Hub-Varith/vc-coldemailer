"""The retrievable world.

Every investor the pipeline can surface exists here only as a set of dated source
documents. Nothing in this module carries a fit score, a rank or a draft — those are
produced downstream by extraction, verification, scoring and drafting. Swap this module
for a live Octen index and the rest of the pipeline is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ...models.evidence import EvidenceKind


@dataclass(frozen=True)
class PartnerRecord:
    id: str
    name: str
    firm: str
    role: str
    location: str
    check_min: int
    check_max: int
    stage: tuple[str, ...]
    sectors: tuple[str, ...]
    last_check_written: date
    prior_contact: str | None = None
    affinities: tuple[str, ...] = ()
    #: Set when the record is known to be decayed. Freshness verification rejects these.
    decay_reason: str | None = None
    decay_detail: str | None = None


@dataclass(frozen=True)
class SourceDocument:
    id: str
    partner_id: str
    kind: EvidenceKind
    claim: str
    detail: str
    published: date
    source_name: str
    source_url: str
    base_strength: int
    tags: tuple[str, ...] = field(default=())


PARTNERS: tuple[PartnerRecord, ...] = (
    PartnerRecord(
        id="maya-chen",
        name="Maya Chen",
        firm="Northstar Ventures",
        role="General Partner",
        location="San Francisco, CA",
        check_min=300_000,
        check_max=800_000,
        stage=("Seed",),
        sectors=("Health Infra", "Hardware"),
        last_check_written=date(2026, 6, 30),
        affinities=("hardware operator",),
    ),
    PartnerRecord(
        id="elias-lind",
        name="Elias Lind",
        firm="Overture Capital",
        role="Partner",
        location="Stockholm, SE",
        check_min=500_000,
        check_max=1_500_000,
        stage=("Seed",),
        sectors=("Consumer Tech", "Audio"),
        last_check_written=date(2026, 7, 8),
        prior_contact="No prior thread — 0 messages in your mailbox.",
    ),
    PartnerRecord(
        id="sarah-jenkins",
        name="Sarah Jenkins",
        firm="Resonance Partners",
        role="Founding Partner",
        location="Austin, TX",
        check_min=250_000,
        check_max=1_000_000,
        stage=("Pre-Seed", "Seed"),
        sectors=("Audio Hardware",),
        last_check_written=date(2026, 5, 27),
    ),
    PartnerRecord(
        id="tomas-berg",
        name="Tomas Berg",
        firm="Kettle & Vane",
        role="Partner",
        location="Berlin, DE",
        check_min=400_000,
        check_max=1_200_000,
        stage=("Seed",),
        sectors=("Hardware", "Supply Chain"),
        last_check_written=date(2026, 7, 2),
        prior_contact="One prior thread — you emailed the firm's general address in March 2026, no reply.",
        affinities=("hardware operator",),
    ),
    PartnerRecord(
        id="priya-raghavan",
        name="Priya Raghavan",
        firm="Lantern Health Fund",
        role="Principal",
        location="Boston, MA",
        check_min=750_000,
        check_max=2_000_000,
        stage=("Seed", "Series A"),
        sectors=("Health Infra", "Accessibility"),
        last_check_written=date(2026, 6, 18),
    ),
    PartnerRecord(
        id="daniel-okoro",
        name="Daniel Okoro",
        firm="Meridian Seed",
        role="Managing Partner",
        location="London, UK",
        check_min=150_000,
        check_max=500_000,
        stage=("Pre-Seed",),
        sectors=("Consumer Tech", "Emerging Markets"),
        last_check_written=date(2026, 7, 14),
    ),
    PartnerRecord(
        id="hannah-vos",
        name="Hannah Vos",
        firm="Tidewater Group",
        role="Partner",
        location="Amsterdam, NL",
        check_min=1_000_000,
        check_max=3_000_000,
        stage=("Seed", "Series A"),
        sectors=("Hardware", "Manufacturing"),
        last_check_written=date(2026, 5, 11),
        affinities=("Lisbon",),
    ),
    PartnerRecord(
        id="marcus-reyes",
        name="Marcus Reyes",
        firm="Foundry Line",
        role="General Partner",
        location="New York, NY",
        check_min=200_000,
        check_max=600_000,
        stage=("Pre-Seed", "Seed"),
        sectors=("Consumer Tech", "Accessibility"),
        last_check_written=date(2026, 6, 5),
        prior_contact="Two prior threads — intro attempted via a shared portfolio founder in January 2026.",
    ),
    PartnerRecord(
        id="lena-fischer",
        name="Lena Fischer",
        firm="Halden Ventures",
        role="Investment Partner",
        location="Copenhagen, DK",
        check_min=300_000,
        check_max=900_000,
        stage=("Seed",),
        sectors=("Health Infra", "Emerging Markets"),
        last_check_written=date(2026, 4, 29),
        affinities=("Lisbon",),
    ),
    PartnerRecord(
        id="arjun-mehta",
        name="Arjun Mehta",
        firm="Beacon Row",
        role="Partner",
        location="San Francisco, CA",
        check_min=500_000,
        check_max=1_500_000,
        stage=("Seed",),
        sectors=("Health Infra",),
        last_check_written=date(2025, 8, 4),
        decay_reason="partner_departed",
        decay_detail="Left Beacon Row in November 2025; firm page still lists the profile.",
    ),
    PartnerRecord(
        id="claire-dubois",
        name="Claire Dubois",
        firm="Rivet Capital",
        role="General Partner",
        location="Paris, FR",
        check_min=400_000,
        check_max=1_000_000,
        stage=("Seed",),
        sectors=("Hardware", "Consumer Tech"),
        last_check_written=date(2025, 3, 19),
        decay_reason="fund_not_deploying",
        decay_detail="No new check in 16 months; Fund II is in wind-down and not making new investments.",
    ),
    PartnerRecord(
        id="peter-nyland",
        name="Peter Nyland",
        firm="Colter Partners",
        role="Principal",
        location="Chicago, IL",
        check_min=250_000,
        check_max=750_000,
        stage=("Seed",),
        sectors=("Consumer Tech",),
        last_check_written=date(2024, 11, 2),
        decay_reason="evidence_stale",
        decay_detail="Only retrievable signal is a 2023 conference bio — re-run returned nothing dated inside the window.",
    ),
)


DOCUMENTS: tuple[SourceDocument, ...] = (
    # Maya Chen — Northstar Ventures
    SourceDocument(
        id="doc-mc-1",
        partner_id="maya-chen",
        kind="thesis_publication",
        claim="Published a thesis on overlooked hearing infrastructure and accessibility markets.",
        detail=(
            'Argues that hearing loss is "the largest untreated sensory market on earth" and that the wedge is '
            "hardware cost, not clinical accuracy. Names bone conduction explicitly as an under-funded modality."
        ),
        published=date(2026, 5, 14),
        source_name='Northstar Field Notes — "The Quiet Market"',
        source_url="https://northstar.vc/notes/the-quiet-market",
        base_strength=94,
        tags=("hearing", "accessibility", "bone conduction", "thesis", "health infra"),
    ),
    SourceDocument(
        id="doc-mc-2",
        partner_id="maya-chen",
        kind="portfolio_investment",
        claim="Led the seed round in Aural Labs, a clinical-grade audiometry startup.",
        detail=(
            "$4.2M seed announced March 2026. Adjacent, not competitive — Aural sells diagnostics into clinics; "
            "Novi sells the device that follows the diagnosis."
        ),
        published=date(2026, 3, 2),
        source_name="TechCrunch — Aural Labs seed announcement",
        source_url="https://techcrunch.com/2026/03/02/aural-labs-seed",
        base_strength=88,
        tags=("hearing", "adjacent portfolio", "audiometry", "seed"),
    ),
    SourceDocument(
        id="doc-mc-3",
        partner_id="maya-chen",
        kind="fund_close",
        claim="Northstar closed Fund IV ($240M) and is actively deploying at seed.",
        detail=(
            "Six checks written in the last 90 days, four of them first-money-in. Stated pace is 14–18 seed "
            "investments from Fund IV."
        ),
        published=date(2026, 1, 21),
        source_name="SEC Form D — Northstar Ventures IV, L.P.",
        source_url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany",
        base_strength=81,
        tags=("fund close", "deploying", "seed"),
    ),
    # Elias Lind — Overture Capital
    SourceDocument(
        id="doc-el-1",
        partner_id="elias-lind",
        kind="portfolio_investment",
        claim="Led the pre-seed round for acoustic spatial mapping startup EchoSpace.",
        detail=(
            "€1.1M pre-seed, February 2026. Signals conviction that audio hardware is a venture-scale category in "
            "Europe, where most generalists treat it as a consumer accessory play."
        ),
        published=date(2026, 2, 2),
        source_name="Sifted — EchoSpace raises €1.1M",
        source_url="https://sifted.eu/articles/echospace-pre-seed",
        base_strength=90,
        tags=("audio hardware", "adjacent portfolio", "wearable audio", "europe"),
    ),
    SourceDocument(
        id="doc-el-2",
        partner_id="elias-lind",
        kind="thesis_publication",
        claim="Argued on the Northbound podcast that hearables are the next platform shift after the watch.",
        detail=(
            'Specifically flags "medical-adjacent hearables that do not require a prescription" as the segment he '
            "wants to own in Overture III."
        ),
        published=date(2026, 4, 19),
        source_name="Northbound Podcast — Episode 112",
        source_url="https://northbound.fm/episodes/112-elias-lind",
        base_strength=85,
        tags=("thesis", "wearable audio", "hearing", "cash-pay medical device"),
    ),
    SourceDocument(
        id="doc-el-3",
        partner_id="elias-lind",
        kind="portfolio_gap",
        claim="Overture holds three audio-adjacent companies and none in hearing assistance.",
        detail=(
            "EchoSpace (spatial audio), Tuner (creator tooling), Kort (in-ear translation). A hearing-assist "
            "position is the visible hole in the map."
        ),
        published=date(2026, 6, 11),
        source_name="Overture Capital — portfolio index",
        source_url="https://overture.capital/portfolio",
        base_strength=76,
        tags=("portfolio gap", "hearing", "audio hardware"),
    ),
    # Sarah Jenkins — Resonance Partners
    SourceDocument(
        id="doc-sj-1",
        partner_id="sarah-jenkins",
        kind="thesis_publication",
        claim='Keynoted "The Next Decade of Wearable Audio" at TechCrunch Disrupt.',
        detail=(
            "Twelve minutes of the talk are about manufacturing cost curves in bone conduction and why the category "
            "stalled at premium price points."
        ),
        published=date(2025, 11, 18),
        source_name="TechCrunch Disrupt 2025 — session recording",
        source_url="https://techcrunch.com/video/disrupt-2025-wearable-audio",
        base_strength=91,
        tags=("thesis", "bone conduction", "wearable audio", "contract manufacturing"),
    ),
    SourceDocument(
        id="doc-sj-2",
        partner_id="sarah-jenkins",
        kind="fund_close",
        claim="Resonance closed a $60M debut fund dedicated to audio and acoustics.",
        detail=(
            "Single-sector fund, first close January 2026. Nine of the first twelve checks went to hardware "
            "companies rather than software."
        ),
        published=date(2026, 1, 9),
        source_name="Axios Pro Rata — Resonance debut fund",
        source_url="https://axios.com/pro-rata/resonance-partners-fund-i",
        base_strength=83,
        tags=("fund close", "audio hardware", "deploying"),
    ),
    SourceDocument(
        id="doc-sj-3",
        partner_id="sarah-jenkins",
        kind="portfolio_investment",
        claim="Backed Cadence Health, a remote hearing-test provider, at pre-seed.",
        detail=(
            "Cadence routes diagnosed users to devices it does not make. The referral path into a low-cost device "
            "is unbuilt on both sides."
        ),
        published=date(2026, 4, 30),
        source_name="Resonance Partners — portfolio note",
        source_url="https://resonance.partners/portfolio/cadence-health",
        base_strength=79,
        tags=("hearing", "adjacent portfolio", "accessibility"),
    ),
    # Tomas Berg — Kettle & Vane
    SourceDocument(
        id="doc-tb-1",
        partner_id="tomas-berg",
        kind="thesis_publication",
        claim="Writes a recurring column on contract manufacturing for early hardware teams.",
        detail=(
            "June entry argues that seed hardware investors should underwrite the BOM, not the demo, and that most "
            "funds cannot read a cost sheet."
        ),
        published=date(2026, 6, 6),
        source_name='Kettle Notes — "Underwrite the BOM"',
        source_url="https://kettlevane.com/notes/underwrite-the-bom",
        base_strength=84,
        tags=("thesis", "contract manufacturing", "hardware", "bill of materials"),
    ),
    SourceDocument(
        id="doc-tb-2",
        partner_id="tomas-berg",
        kind="portfolio_investment",
        claim="Backed Fathom Instruments, a low-cost medical device manufacturer in Porto.",
        detail=(
            "Same manufacturing corridor Novi uses. Fathom proved the Iberian contract-manufacturing route to "
            "sub-$200 medical hardware."
        ),
        published=date(2025, 10, 15),
        source_name="EU-Startups — Fathom Instruments seed",
        source_url="https://www.eu-startups.com/2025/10/fathom-instruments-seed",
        base_strength=80,
        tags=("adjacent portfolio", "contract manufacturing", "cash-pay medical device", "europe"),
    ),
    SourceDocument(
        id="doc-tb-3",
        partner_id="tomas-berg",
        kind="fund_close",
        claim="Kettle & Vane announced a €90M second fund and resumed deploying in May 2026.",
        detail="Paused new investments for eight months in 2025; the pause ended with the Fund II first close.",
        published=date(2026, 5, 4),
        source_name="Kettle & Vane — fund announcement",
        source_url="https://kettlevane.com/fund-ii",
        base_strength=74,
        tags=("fund close", "deploying", "europe"),
    ),
    # Priya Raghavan — Lantern Health Fund
    SourceDocument(
        id="doc-pr-1",
        partner_id="priya-raghavan",
        kind="thesis_publication",
        claim="Published research on reimbursement-free medical devices in emerging markets.",
        detail=(
            "Concludes that devices priced under $250 cash-pay outperform reimbursed equivalents on actual adoption "
            "in eight of eleven markets studied."
        ),
        published=date(2026, 5, 28),
        source_name='Lantern Research — "Cash-Pay Wins"',
        source_url="https://lanternhealth.fund/research/cash-pay-wins",
        base_strength=88,
        tags=("thesis", "cash-pay medical device", "health infra", "emerging markets"),
    ),
    SourceDocument(
        id="doc-pr-2",
        partner_id="priya-raghavan",
        kind="portfolio_gap",
        claim="Lantern holds seven accessibility companies, all software.",
        detail=(
            "Screen readers, captioning, mobility routing. No hardware position at all, which she called "
            '"the obvious gap" at HLTH 2026.'
        ),
        published=date(2026, 6, 25),
        source_name="HLTH 2026 — panel transcript",
        source_url="https://hlth.com/2026/sessions/accessibility-capital",
        base_strength=81,
        tags=("portfolio gap", "accessibility", "hardware"),
    ),
    SourceDocument(
        id="doc-pr-3",
        partner_id="priya-raghavan",
        kind="exit",
        claim="Rode the Auricle acquisition by a major hearing-aid manufacturer.",
        detail=(
            "Auricle sold for a reported $310M in September 2025. She has already run the diligence playbook on "
            "this exact buyer set."
        ),
        published=date(2025, 9, 12),
        source_name="Fierce Biotech — Auricle acquisition",
        source_url="https://www.fiercebiotech.com/medtech/auricle-acquisition",
        base_strength=77,
        tags=("relevant exit", "hearing", "health infra"),
    ),
    # Daniel Okoro — Meridian Seed
    SourceDocument(
        id="doc-do-1",
        partner_id="daniel-okoro",
        kind="thesis_publication",
        claim="Runs a public memo series on distribution-first hardware in emerging markets.",
        detail=(
            "March memo: the winning pattern is a device sold through existing pharmacy and telecom retail, not "
            "through clinical channels."
        ),
        published=date(2026, 3, 27),
        source_name='Meridian Memos — "Shelf Space First"',
        source_url="https://meridianseed.com/memos/shelf-space-first",
        base_strength=82,
        tags=("thesis", "emerging markets", "accessibility hardware", "distribution"),
    ),
    SourceDocument(
        id="doc-do-2",
        partner_id="daniel-okoro",
        kind="portfolio_investment",
        claim="Backed Kiosk Health, which distributes diagnostics through pharmacy counters.",
        detail=(
            "Kiosk operates 1,900 pharmacy counters across three markets — the same shelf Novi needs for retail "
            "distribution."
        ),
        published=date(2026, 2, 19),
        source_name="Meridian Seed — Kiosk Health announcement",
        source_url="https://meridianseed.com/portfolio/kiosk-health",
        base_strength=78,
        tags=("adjacent portfolio", "distribution", "emerging markets", "cash-pay medical device"),
    ),
    SourceDocument(
        id="doc-do-3",
        partner_id="daniel-okoro",
        kind="fund_close",
        claim="Meridian is deploying from a $35M rolling vehicle with a two-week decision cycle.",
        detail="Publicly commits to a decision within ten business days of first call. Eleven checks year to date.",
        published=date(2026, 6, 1),
        source_name="Meridian Seed — how we invest",
        source_url="https://meridianseed.com/how-we-invest",
        base_strength=70,
        tags=("fund close", "deploying", "pre-seed"),
    ),
    # Hannah Vos — Tidewater Group
    SourceDocument(
        id="doc-hv-1",
        partner_id="hannah-vos",
        kind="portfolio_investment",
        claim="Led a Series A in Verge Robotics, a Portuguese precision-assembly company.",
        detail=(
            "€8M round, December 2025. Verge assembles the exact class of miniature transducer housing Novi ships "
            "in volume."
        ),
        published=date(2025, 12, 4),
        source_name="Tidewater Group — Verge Robotics Series A",
        source_url="https://tidewater.group/news/verge-robotics-series-a",
        base_strength=80,
        tags=("adjacent portfolio", "contract manufacturing", "europe", "hardware"),
    ),
    SourceDocument(
        id="doc-hv-2",
        partner_id="hannah-vos",
        kind="thesis_publication",
        claim="Told Bloomberg that European hardware seed rounds are structurally underpriced.",
        detail=(
            "Says Tidewater will write earlier checks than its mandate suggests when the manufacturing route is "
            "already proven."
        ),
        published=date(2026, 4, 8),
        source_name="Bloomberg — European hardware funding",
        source_url="https://www.bloomberg.com/news/articles/2026-04-08/european-hardware-seed",
        base_strength=72,
        tags=("thesis", "europe", "hardware", "geography crossing"),
    ),
    SourceDocument(
        id="doc-hv-3",
        partner_id="hannah-vos",
        kind="portfolio_gap",
        claim="Tidewater has no consumer-facing medical device in the portfolio.",
        detail="Eleven industrial and component companies, zero consumer endpoints. Portfolio review published June 2026.",
        published=date(2026, 6, 15),
        source_name="Tidewater Group — 2026 portfolio review",
        source_url="https://tidewater.group/portfolio-review-2026",
        base_strength=68,
        tags=("portfolio gap", "cash-pay medical device", "hardware"),
    ),
    # Marcus Reyes — Foundry Line
    SourceDocument(
        id="doc-mr-1",
        partner_id="marcus-reyes",
        kind="thesis_publication",
        claim="Opened an accessibility-focused investment track after a public commitment in February.",
        detail=(
            "Committed 20% of the current fund to accessibility companies with a named preference for physical "
            "products over apps."
        ),
        published=date(2026, 2, 11),
        source_name="Foundry Line — accessibility commitment",
        source_url="https://foundryline.com/accessibility-track",
        base_strength=79,
        tags=("thesis", "accessibility", "accessibility hardware"),
    ),
    SourceDocument(
        id="doc-mr-2",
        partner_id="marcus-reyes",
        kind="portfolio_investment",
        claim="Backed Signal Cane, a haptic navigation device for blind users.",
        detail="First hardware check from the accessibility track, April 2026. Same buyer psychology, different sense.",
        published=date(2026, 4, 22),
        source_name="Foundry Line — Signal Cane pre-seed",
        source_url="https://foundryline.com/portfolio/signal-cane",
        base_strength=75,
        tags=("adjacent portfolio", "accessibility", "accessibility hardware"),
    ),
    SourceDocument(
        id="doc-mr-3",
        partner_id="marcus-reyes",
        kind="portfolio_gap",
        claim="The accessibility track has no hearing company after five months.",
        detail=(
            "Four investments so far: vision, mobility, cognitive, speech. Hearing is the remaining category on his "
            "own stated map."
        ),
        published=date(2026, 7, 9),
        source_name="Foundry Line — track update, July 2026",
        source_url="https://foundryline.com/track-update-july-2026",
        base_strength=71,
        tags=("portfolio gap", "hearing", "accessibility"),
    ),
    # Lena Fischer — Halden Ventures
    SourceDocument(
        id="doc-lf-1",
        partner_id="lena-fischer",
        kind="fund_close",
        claim="Halden closed a €120M fund with a mandate for global-south health distribution.",
        detail="LP base includes two development finance institutions requiring deployment outside Western Europe.",
        published=date(2026, 3, 16),
        source_name="Halden Ventures — Fund III close",
        source_url="https://haldenventures.com/fund-iii",
        base_strength=76,
        tags=("fund close", "emerging markets", "health infra", "geography crossing"),
    ),
    SourceDocument(
        id="doc-lf-2",
        partner_id="lena-fischer",
        kind="thesis_publication",
        claim="Wrote that assistive devices are the highest-leverage health category per euro deployed.",
        detail=(
            "Quantifies cost per disability-adjusted life year for hearing devices at roughly a fifth of comparable "
            "interventions."
        ),
        published=date(2026, 5, 2),
        source_name='Halden Journal — "Leverage per Euro"',
        source_url="https://haldenventures.com/journal/leverage-per-euro",
        base_strength=73,
        tags=("thesis", "hearing", "accessibility", "health infra"),
    ),
    SourceDocument(
        id="doc-lf-3",
        partner_id="lena-fischer",
        kind="portfolio_investment",
        claim="Invested in Ansu Diagnostics, distributing point-of-care tests across five markets.",
        detail="Proves the fund underwrites physical distribution in exactly the markets Novi targets after Iberia.",
        published=date(2026, 1, 30),
        source_name="Halden Ventures — Ansu Diagnostics",
        source_url="https://haldenventures.com/portfolio/ansu-diagnostics",
        base_strength=69,
        tags=("adjacent portfolio", "emerging markets", "distribution"),
    ),
    # Decayed records — retrievable, but rejected at the freshness gate.
    SourceDocument(
        id="doc-am-1",
        partner_id="arjun-mehta",
        kind="thesis_publication",
        claim="Spoke on hearing-adjacent medtech at a 2025 health conference.",
        detail="Panel appearance listed on the firm's events page; the profile has not been updated since.",
        published=date(2025, 6, 12),
        source_name="Beacon Row — events archive",
        source_url="https://beaconrow.com/events/2025-medtech-panel",
        base_strength=64,
        tags=("thesis", "hearing", "health infra"),
    ),
    SourceDocument(
        id="doc-cd-1",
        partner_id="claire-dubois",
        kind="portfolio_investment",
        claim="Backed a consumer audio wearable in the 2024 vintage.",
        detail="Last publicly visible investment from Rivet's Fund II, which has since stopped making new checks.",
        published=date(2024, 9, 3),
        source_name="Rivet Capital — portfolio",
        source_url="https://rivetcapital.fr/portefeuille",
        base_strength=61,
        tags=("adjacent portfolio", "wearable audio", "europe"),
    ),
    SourceDocument(
        id="doc-pn-1",
        partner_id="peter-nyland",
        kind="thesis_publication",
        claim="Listed hearing tech as an interest area in a conference speaker bio.",
        detail="A speaker-bio interest list is not a dated, retrievable fact about deployment or thesis.",
        published=date(2023, 10, 21),
        source_name="Midwest Venture Summit — speaker bio",
        source_url="https://midwestventuresummit.com/2023/speakers",
        base_strength=52,
        tags=("thesis", "hearing"),
    ),
)


PARTNERS_BY_ID = {p.id: p for p in PARTNERS}


def documents_for(partner_id: str) -> list[SourceDocument]:
    return [d for d in DOCUMENTS if d.partner_id == partner_id]
