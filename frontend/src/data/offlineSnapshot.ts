import type { DraftPublic, RunStatus, TargetDetail, TargetSummary } from '../types'

/**
 * Offline snapshot of a real pipeline run, captured from the API.
 * Used only when the backend is unreachable so the workspace still demonstrates the flow.
 */
const snapshot = {
  "run": {
    "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
    "profile_id": "06382987-fc18-4345-97e0-24e11c8f7c2e",
    "status": "complete",
    "stage": "complete",
    "progress": {
      "queries_total": 522,
      "queries_done": 522,
      "results": 3070,
      "evidence": 28,
      "investors": 9
    },
    "retrieval_stats": {
      "queries_planned": 522,
      "queries_issued": 522,
      "queries_deduped": 0,
      "cache_hits": 522,
      "failed_queries": 0,
      "results": 3070,
      "wall_time_ms": 11,
      "p50_latency_ms": 0,
      "p95_latency_ms": 0,
      "max_concurrency": 0,
      "content_extractions": 23,
      "transport": "local_index"
    },
    "warnings": [
      "list_underfilled"
    ],
    "started_at": "2026-07-24T01:25:06.562862Z",
    "completed_at": "2026-07-24T01:25:06.684145Z",
    "list_underfilled": true,
    "rejected_count": 2,
    "sources_searched": 28,
    "error": null
  },
  "rows": [
    {
      "target_id": "bed0f710-a81a-4295-ac90-30136ef048a6",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Overture Capital",
      "investor_person": "Elias Lind",
      "role": "Partner",
      "score": 0.97,
      "status": "new",
      "contact_email": "elias@overturecapital.com",
      "firm_domain": "sifted.eu",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "7e5aac81-9a93-43c9-9a9f-d50d0d679648",
        "investor_firm": "Overture Capital",
        "investor_person": "Elias Lind",
        "kind": "thesis_publication",
        "claim": "Argued on the Northbound podcast that hearables are the next platform shift after the watch.",
        "detail": "Specifically flags \"medical-adjacent hearables that do not require a prescription\" as the segment he wants to own in Overture III.",
        "event_date": "2026-04-19",
        "source_url": "https://northbound.fm/episodes/112-elias-lind",
        "source_name": "Northbound Podcast \u2014 Episode 112",
        "source_published_at": "2026-04-19",
        "confidence": 0.85,
        "verified_at": "2026-07-24T01:25:06.653078Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "Stockholm, SE",
      "check_min": 500000,
      "check_max": 1500000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Consumer Tech",
        "Audio"
      ],
      "draft_id": null
    },
    {
      "target_id": "96516b0c-87c2-4539-a4c3-c2e197ea0e27",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Northstar Ventures",
      "investor_person": "Maya Chen",
      "role": "General Partner",
      "score": 0.9472,
      "status": "new",
      "contact_email": "maya@northstarventures.com",
      "firm_domain": "northstar.vc",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "f51b6606-8d7d-4c80-9a0c-08a0789cb510",
        "investor_firm": "Northstar Ventures",
        "investor_person": "Maya Chen",
        "kind": "thesis_publication",
        "claim": "Published a thesis on overlooked hearing infrastructure and accessibility markets.",
        "detail": "Argues that hearing loss is \"the largest untreated sensory market on earth\" and that the wedge is hardware cost, not clinical accuracy. Names bone conduction explicitly as an under-funded modality.",
        "event_date": "2026-05-14",
        "source_url": "https://northstar.vc/notes/the-quiet-market",
        "source_name": "Northstar Field Notes \u2014 \"The Quiet Market\"",
        "source_published_at": "2026-05-14",
        "confidence": 0.94,
        "verified_at": "2026-07-24T01:25:06.653024Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "San Francisco, CA",
      "check_min": 300000,
      "check_max": 800000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Health Infra",
        "Hardware"
      ],
      "draft_id": null
    },
    {
      "target_id": "a687b5ad-e9e3-4497-bb43-ffa813e0c634",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Foundry Line",
      "investor_person": "Marcus Reyes",
      "role": "General Partner",
      "score": 0.915,
      "status": "new",
      "contact_email": "marcus@foundryline.com",
      "firm_domain": "foundryline.com",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "8a1fcedc-b667-4c15-a103-3fad007372aa",
        "investor_firm": "Foundry Line",
        "investor_person": "Marcus Reyes",
        "kind": "portfolio_gap",
        "claim": "The accessibility track has no hearing company after five months.",
        "detail": "Four investments so far: vision, mobility, cognitive, speech. Hearing is the remaining category on his own stated map.",
        "event_date": "2026-07-09",
        "source_url": "https://foundryline.com/track-update-july-2026",
        "source_name": "Foundry Line \u2014 track update, July 2026",
        "source_published_at": "2026-07-09",
        "confidence": 0.71,
        "verified_at": "2026-07-24T01:25:06.653252Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "New York, NY",
      "check_min": 200000,
      "check_max": 600000,
      "stage": [
        "Pre-Seed",
        "Seed"
      ],
      "sectors": [
        "Consumer Tech",
        "Accessibility"
      ],
      "draft_id": null
    },
    {
      "target_id": "c60f03db-a5af-4fb6-8455-ff37181782f9",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Lantern Health Fund",
      "investor_person": "Priya Raghavan",
      "role": "Principal",
      "score": 0.909,
      "status": "new",
      "contact_email": "priya@lanternhealthfund.com",
      "firm_domain": "www.fiercebiotech.com",
      "evidence_count": 3,
      "has_stale_evidence": false,
      "lead_evidence": {
        "id": "3972062c-ae56-49fa-8526-235e62406b20",
        "investor_firm": "Lantern Health Fund",
        "investor_person": "Priya Raghavan",
        "kind": "thesis_publication",
        "claim": "Published research on reimbursement-free medical devices in emerging markets.",
        "detail": "Concludes that devices priced under $250 cash-pay outperform reimbursed equivalents on actual adoption in eight of eleven markets studied.",
        "event_date": "2026-05-28",
        "source_url": "https://lanternhealth.fund/research/cash-pay-wins",
        "source_name": "Lantern Research \u2014 \"Cash-Pay Wins\"",
        "source_published_at": "2026-05-28",
        "confidence": 0.88,
        "verified_at": "2026-07-24T01:25:06.653273Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "Boston, MA",
      "check_min": 750000,
      "check_max": 2000000,
      "stage": [
        "Seed",
        "Series A"
      ],
      "sectors": [
        "Health Infra",
        "Accessibility"
      ],
      "draft_id": null
    },
    {
      "target_id": "9945e811-4619-41b1-be2c-dfbfe760f06b",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Kettle & Vane",
      "investor_person": "Tomas Berg",
      "role": "Partner",
      "score": 0.8634,
      "status": "new",
      "contact_email": "tomas@kettlevane.com",
      "firm_domain": "www.eu-startups.com",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "c0fe98d7-d3cc-47c7-88d7-a8e720af0721",
        "investor_firm": "Kettle & Vane",
        "investor_person": "Tomas Berg",
        "kind": "thesis_publication",
        "claim": "Writes a recurring column on contract manufacturing for early hardware teams.",
        "detail": "June entry argues that seed hardware investors should underwrite the BOM, not the demo, and that most funds cannot read a cost sheet.",
        "event_date": "2026-06-06",
        "source_url": "https://kettlevane.com/notes/underwrite-the-bom",
        "source_name": "Kettle Notes \u2014 \"Underwrite the BOM\"",
        "source_published_at": "2026-06-06",
        "confidence": 0.84,
        "verified_at": "2026-07-24T01:25:06.653304Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "Berlin, DE",
      "check_min": 400000,
      "check_max": 1200000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Hardware",
        "Supply Chain"
      ],
      "draft_id": null
    },
    {
      "target_id": "dfdebe89-70d8-4b16-b632-3d4d58a39066",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Meridian Seed",
      "investor_person": "Daniel Okoro",
      "role": "Managing Partner",
      "score": 0.8513,
      "status": "new",
      "contact_email": "daniel@meridianseed.com",
      "firm_domain": "meridianseed.com",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "4f74dc2a-2565-4b40-8617-5371e6bc208a",
        "investor_firm": "Meridian Seed",
        "investor_person": "Daniel Okoro",
        "kind": "thesis_publication",
        "claim": "Runs a public memo series on distribution-first hardware in emerging markets.",
        "detail": "March memo: the winning pattern is a device sold through existing pharmacy and telecom retail, not through clinical channels.",
        "event_date": "2026-03-27",
        "source_url": "https://meridianseed.com/memos/shelf-space-first",
        "source_name": "Meridian Memos \u2014 \"Shelf Space First\"",
        "source_published_at": "2026-03-27",
        "confidence": 0.82,
        "verified_at": "2026-07-24T01:25:06.653233Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "London, UK",
      "check_min": 150000,
      "check_max": 500000,
      "stage": [
        "Pre-Seed"
      ],
      "sectors": [
        "Consumer Tech",
        "Emerging Markets"
      ],
      "draft_id": null
    },
    {
      "target_id": "62983e7f-2cb9-42ff-bd5d-3b79839ae77d",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Tidewater Group",
      "investor_person": "Hannah Vos",
      "role": "Partner",
      "score": 0.7974,
      "status": "new",
      "contact_email": "hannah@tidewatergroup.com",
      "firm_domain": "tidewater.group",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "ae108de7-a61d-42f0-8ac5-a69089f0b6b8",
        "investor_firm": "Tidewater Group",
        "investor_person": "Hannah Vos",
        "kind": "thesis_publication",
        "claim": "Told Bloomberg that European hardware seed rounds are structurally underpriced.",
        "detail": "Says Tidewater will write earlier checks than its mandate suggests when the manufacturing route is already proven.",
        "event_date": "2026-04-08",
        "source_url": "https://www.bloomberg.com/news/articles/2026-04-08/european-hardware-seed",
        "source_name": "Bloomberg \u2014 European hardware funding",
        "source_published_at": "2026-04-08",
        "confidence": 0.72,
        "verified_at": "2026-07-24T01:25:06.653262Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "Amsterdam, NL",
      "check_min": 1000000,
      "check_max": 3000000,
      "stage": [
        "Seed",
        "Series A"
      ],
      "sectors": [
        "Hardware",
        "Manufacturing"
      ],
      "draft_id": null
    },
    {
      "target_id": "b83ba536-ca57-4466-a5e6-1d87cbd5200c",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Resonance Partners",
      "investor_person": "Sarah Jenkins",
      "role": "Founding Partner",
      "score": 0.744,
      "status": "new",
      "contact_email": "sarah@resonancepartners.com",
      "firm_domain": "techcrunch.com",
      "evidence_count": 3,
      "has_stale_evidence": true,
      "lead_evidence": {
        "id": "0993e942-20cb-4440-bae3-f9fa8303616a",
        "investor_firm": "Resonance Partners",
        "investor_person": "Sarah Jenkins",
        "kind": "portfolio_investment",
        "claim": "Backed Cadence Health, a remote hearing-test provider, at pre-seed.",
        "detail": "Cadence routes diagnosed users to devices it does not make. The referral path into a low-cost device is unbuilt on both sides.",
        "event_date": "2026-04-30",
        "source_url": "https://resonance.partners/portfolio/cadence-health",
        "source_name": "Resonance Partners \u2014 portfolio note",
        "source_published_at": "2026-04-30",
        "confidence": 0.79,
        "verified_at": "2026-07-24T01:25:06.653063Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "Austin, TX",
      "check_min": 250000,
      "check_max": 1000000,
      "stage": [
        "Pre-Seed",
        "Seed"
      ],
      "sectors": [
        "Audio Hardware"
      ],
      "draft_id": null
    },
    {
      "target_id": "1de73ed7-5b6a-4ee8-9815-eb2a09940a10",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Halden Ventures",
      "investor_person": "Lena Fischer",
      "role": "Investment Partner",
      "score": 0.5289,
      "status": "new",
      "contact_email": "lena@haldenventures.com",
      "firm_domain": "haldenventures.com",
      "evidence_count": 2,
      "has_stale_evidence": false,
      "lead_evidence": {
        "id": "776007a7-ae47-4b05-9abc-c6b003885e12",
        "investor_firm": "Halden Ventures",
        "investor_person": "Lena Fischer",
        "kind": "thesis_publication",
        "claim": "Wrote that assistive devices are the highest-leverage health category per euro deployed.",
        "detail": "Quantifies cost per disability-adjusted life year for hearing devices at roughly a fifth of comparable interventions.",
        "event_date": "2026-05-02",
        "source_url": "https://haldenventures.com/journal/leverage-per-euro",
        "source_name": "Halden Journal \u2014 \"Leverage per Euro\"",
        "source_published_at": "2026-05-02",
        "confidence": 0.73,
        "verified_at": "2026-07-24T01:25:06.653283Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "location": "Copenhagen, DK",
      "check_min": 300000,
      "check_max": 900000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Health Infra",
        "Emerging Markets"
      ],
      "draft_id": null
    }
  ],
  "details": [
    {
      "target_id": "bed0f710-a81a-4295-ac90-30136ef048a6",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Overture Capital",
      "investor_person": "Elias Lind",
      "role": "Partner",
      "score": 0.97,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "7e5aac81-9a93-43c9-9a9f-d50d0d679648",
          "investor_firm": "Overture Capital",
          "investor_person": "Elias Lind",
          "kind": "thesis_publication",
          "claim": "Argued on the Northbound podcast that hearables are the next platform shift after the watch.",
          "detail": "Specifically flags \"medical-adjacent hearables that do not require a prescription\" as the segment he wants to own in Overture III.",
          "event_date": "2026-04-19",
          "source_url": "https://northbound.fm/episodes/112-elias-lind",
          "source_name": "Northbound Podcast \u2014 Episode 112",
          "source_published_at": "2026-04-19",
          "confidence": 0.85,
          "verified_at": "2026-07-24T01:25:06.653078Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "e02bee8c-5150-41a1-b3b9-a3f2f79cbd2e",
          "investor_firm": "Overture Capital",
          "investor_person": "Elias Lind",
          "kind": "portfolio_gap",
          "claim": "Overture holds three audio-adjacent companies and none in hearing assistance.",
          "detail": "EchoSpace (spatial audio), Tuner (creator tooling), Kort (in-ear translation). A hearing-assist position is the visible hole in the map.",
          "event_date": "2026-06-11",
          "source_url": "https://overture.capital/portfolio",
          "source_name": "Overture Capital \u2014 portfolio index",
          "source_published_at": "2026-06-11",
          "confidence": 0.76,
          "verified_at": "2026-07-24T01:25:06.653078Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "355d0179-8925-4034-984f-25deaf286005",
          "investor_firm": "Overture Capital",
          "investor_person": "Elias Lind",
          "kind": "portfolio_investment",
          "claim": "Led the pre-seed round for acoustic spatial mapping startup EchoSpace.",
          "detail": "\u20ac1.1M pre-seed, February 2026. Signals conviction that audio hardware is a venture-scale category in Europe, where most generalists treat it as a consumer accessory play.",
          "event_date": "2026-02-02",
          "source_url": "https://sifted.eu/articles/echospace-pre-seed",
          "source_name": "Sifted \u2014 EchoSpace raises \u20ac1.1M",
          "source_published_at": "2026-02-02",
          "confidence": 0.9,
          "verified_at": "2026-07-24T01:25:06.653078Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "7e5aac81-9a93-43c9-9a9f-d50d0d679648",
        "investor_firm": "Overture Capital",
        "investor_person": "Elias Lind",
        "kind": "thesis_publication",
        "claim": "Argued on the Northbound podcast that hearables are the next platform shift after the watch.",
        "detail": "Specifically flags \"medical-adjacent hearables that do not require a prescription\" as the segment he wants to own in Overture III.",
        "event_date": "2026-04-19",
        "source_url": "https://northbound.fm/episodes/112-elias-lind",
        "source_name": "Northbound Podcast \u2014 Episode 112",
        "source_published_at": "2026-04-19",
        "confidence": 0.85,
        "verified_at": "2026-07-24T01:25:06.653078Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "elias@overturecapital.com",
      "firm_domain": "sifted.eu",
      "list_underfilled": true,
      "location": "Stockholm, SE",
      "check_min": 500000,
      "check_max": 1500000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Consumer Tech",
        "Audio"
      ],
      "score_breakdown": {
        "evidence_strength": 1.5494,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.6936,
        "records": 3.0,
        "normalized": 1.0,
        "affinity_tiebreak": 0.0
      },
      "draft_id": null
    },
    {
      "target_id": "96516b0c-87c2-4539-a4c3-c2e197ea0e27",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Northstar Ventures",
      "investor_person": "Maya Chen",
      "role": "General Partner",
      "score": 0.9472,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "f51b6606-8d7d-4c80-9a0c-08a0789cb510",
          "investor_firm": "Northstar Ventures",
          "investor_person": "Maya Chen",
          "kind": "thesis_publication",
          "claim": "Published a thesis on overlooked hearing infrastructure and accessibility markets.",
          "detail": "Argues that hearing loss is \"the largest untreated sensory market on earth\" and that the wedge is hardware cost, not clinical accuracy. Names bone conduction explicitly as an under-funded modality.",
          "event_date": "2026-05-14",
          "source_url": "https://northstar.vc/notes/the-quiet-market",
          "source_name": "Northstar Field Notes \u2014 \"The Quiet Market\"",
          "source_published_at": "2026-05-14",
          "confidence": 0.94,
          "verified_at": "2026-07-24T01:25:06.653024Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "73ac0138-cc18-462d-93b9-b9affbda95f3",
          "investor_firm": "Northstar Ventures",
          "investor_person": "Maya Chen",
          "kind": "portfolio_investment",
          "claim": "Led the seed round in Aural Labs, a clinical-grade audiometry startup.",
          "detail": "$4.2M seed announced March 2026. Adjacent, not competitive \u2014 Aural sells diagnostics into clinics; Novi sells the device that follows the diagnosis.",
          "event_date": "2026-03-02",
          "source_url": "https://techcrunch.com/2026/03/02/aural-labs-seed",
          "source_name": "TechCrunch \u2014 Aural Labs seed announcement",
          "source_published_at": "2026-03-02",
          "confidence": 0.88,
          "verified_at": "2026-07-24T01:25:06.653024Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "06a95b64-03b8-4cf1-a5d9-ef501bfaf797",
          "investor_firm": "Northstar Ventures",
          "investor_person": "Maya Chen",
          "kind": "fund_close",
          "claim": "Northstar closed Fund IV ($240M) and is actively deploying at seed.",
          "detail": "Six checks written in the last 90 days, four of them first-money-in. Stated pace is 14\u201318 seed investments from Fund IV.",
          "event_date": "2026-01-21",
          "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany",
          "source_name": "SEC Form D \u2014 Northstar Ventures IV, L.P.",
          "source_published_at": "2026-01-21",
          "confidence": 0.81,
          "verified_at": "2026-07-24T01:25:06.653024Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "f51b6606-8d7d-4c80-9a0c-08a0789cb510",
        "investor_firm": "Northstar Ventures",
        "investor_person": "Maya Chen",
        "kind": "thesis_publication",
        "claim": "Published a thesis on overlooked hearing infrastructure and accessibility markets.",
        "detail": "Argues that hearing loss is \"the largest untreated sensory market on earth\" and that the wedge is hardware cost, not clinical accuracy. Names bone conduction explicitly as an under-funded modality.",
        "event_date": "2026-05-14",
        "source_url": "https://northstar.vc/notes/the-quiet-market",
        "source_name": "Northstar Field Notes \u2014 \"The Quiet Market\"",
        "source_published_at": "2026-05-14",
        "confidence": 0.94,
        "verified_at": "2026-07-24T01:25:06.653024Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "maya@northstarventures.com",
      "firm_domain": "northstar.vc",
      "list_underfilled": true,
      "location": "San Francisco, CA",
      "check_min": 300000,
      "check_max": 800000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Health Infra",
        "Hardware"
      ],
      "score_breakdown": {
        "evidence_strength": 1.5002,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.7637,
        "records": 3.0,
        "normalized": 0.9682,
        "affinity_tiebreak": 0.008
      },
      "draft_id": null
    },
    {
      "target_id": "a687b5ad-e9e3-4497-bb43-ffa813e0c634",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Foundry Line",
      "investor_person": "Marcus Reyes",
      "role": "General Partner",
      "score": 0.915,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "8a1fcedc-b667-4c15-a103-3fad007372aa",
          "investor_firm": "Foundry Line",
          "investor_person": "Marcus Reyes",
          "kind": "portfolio_gap",
          "claim": "The accessibility track has no hearing company after five months.",
          "detail": "Four investments so far: vision, mobility, cognitive, speech. Hearing is the remaining category on his own stated map.",
          "event_date": "2026-07-09",
          "source_url": "https://foundryline.com/track-update-july-2026",
          "source_name": "Foundry Line \u2014 track update, July 2026",
          "source_published_at": "2026-07-09",
          "confidence": 0.71,
          "verified_at": "2026-07-24T01:25:06.653252Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "f6783968-11ac-4aa4-a62a-3d0f2b4c0b13",
          "investor_firm": "Foundry Line",
          "investor_person": "Marcus Reyes",
          "kind": "portfolio_investment",
          "claim": "Backed Signal Cane, a haptic navigation device for blind users.",
          "detail": "First hardware check from the accessibility track, April 2026. Same buyer psychology, different sense.",
          "event_date": "2026-04-22",
          "source_url": "https://foundryline.com/portfolio/signal-cane",
          "source_name": "Foundry Line \u2014 Signal Cane pre-seed",
          "source_published_at": "2026-04-22",
          "confidence": 0.75,
          "verified_at": "2026-07-24T01:25:06.653252Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "93b7e50b-53ce-43af-9c98-2b3b2897264b",
          "investor_firm": "Foundry Line",
          "investor_person": "Marcus Reyes",
          "kind": "thesis_publication",
          "claim": "Opened an accessibility-focused investment track after a public commitment in February.",
          "detail": "Committed 20% of the current fund to accessibility companies with a named preference for physical products over apps.",
          "event_date": "2026-02-11",
          "source_url": "https://foundryline.com/accessibility-track",
          "source_name": "Foundry Line \u2014 accessibility commitment",
          "source_published_at": "2026-02-11",
          "confidence": 0.79,
          "verified_at": "2026-07-24T01:25:06.653252Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "8a1fcedc-b667-4c15-a103-3fad007372aa",
        "investor_firm": "Foundry Line",
        "investor_person": "Marcus Reyes",
        "kind": "portfolio_gap",
        "claim": "The accessibility track has no hearing company after five months.",
        "detail": "Four investments so far: vision, mobility, cognitive, speech. Hearing is the remaining category on his own stated map.",
        "event_date": "2026-07-09",
        "source_url": "https://foundryline.com/track-update-july-2026",
        "source_name": "Foundry Line \u2014 track update, July 2026",
        "source_published_at": "2026-07-09",
        "confidence": 0.71,
        "verified_at": "2026-07-24T01:25:06.653252Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "marcus@foundryline.com",
      "firm_domain": "foundryline.com",
      "list_underfilled": true,
      "location": "New York, NY",
      "check_min": 200000,
      "check_max": 600000,
      "stage": [
        "Pre-Seed",
        "Seed"
      ],
      "sectors": [
        "Consumer Tech",
        "Accessibility"
      ],
      "score_breakdown": {
        "evidence_strength": 1.4615,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.9475,
        "records": 3.0,
        "normalized": 0.9433,
        "affinity_tiebreak": 0.0
      },
      "draft_id": null
    },
    {
      "target_id": "c60f03db-a5af-4fb6-8455-ff37181782f9",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Lantern Health Fund",
      "investor_person": "Priya Raghavan",
      "role": "Principal",
      "score": 0.909,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "3972062c-ae56-49fa-8526-235e62406b20",
          "investor_firm": "Lantern Health Fund",
          "investor_person": "Priya Raghavan",
          "kind": "thesis_publication",
          "claim": "Published research on reimbursement-free medical devices in emerging markets.",
          "detail": "Concludes that devices priced under $250 cash-pay outperform reimbursed equivalents on actual adoption in eight of eleven markets studied.",
          "event_date": "2026-05-28",
          "source_url": "https://lanternhealth.fund/research/cash-pay-wins",
          "source_name": "Lantern Research \u2014 \"Cash-Pay Wins\"",
          "source_published_at": "2026-05-28",
          "confidence": 0.88,
          "verified_at": "2026-07-24T01:25:06.653273Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "2d28ad11-047b-484d-877c-2e3074f9ec54",
          "investor_firm": "Lantern Health Fund",
          "investor_person": "Priya Raghavan",
          "kind": "portfolio_gap",
          "claim": "Lantern holds seven accessibility companies, all software.",
          "detail": "Screen readers, captioning, mobility routing. No hardware position at all, which she called \"the obvious gap\" at HLTH 2026.",
          "event_date": "2026-06-25",
          "source_url": "https://hlth.com/2026/sessions/accessibility-capital",
          "source_name": "HLTH 2026 \u2014 panel transcript",
          "source_published_at": "2026-06-25",
          "confidence": 0.81,
          "verified_at": "2026-07-24T01:25:06.653273Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "09ba3ab9-864d-47f4-9f69-53ef9efcb841",
          "investor_firm": "Lantern Health Fund",
          "investor_person": "Priya Raghavan",
          "kind": "exit",
          "claim": "Rode the Auricle acquisition by a major hearing-aid manufacturer.",
          "detail": "Auricle sold for a reported $310M in September 2025. She has already run the diligence playbook on this exact buyer set.",
          "event_date": "2025-09-12",
          "source_url": "https://www.fiercebiotech.com/medtech/auricle-acquisition",
          "source_name": "Fierce Biotech \u2014 Auricle acquisition",
          "source_published_at": "2025-09-12",
          "confidence": 0.77,
          "verified_at": "2026-07-24T01:25:06.653273Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "3972062c-ae56-49fa-8526-235e62406b20",
        "investor_firm": "Lantern Health Fund",
        "investor_person": "Priya Raghavan",
        "kind": "thesis_publication",
        "claim": "Published research on reimbursement-free medical devices in emerging markets.",
        "detail": "Concludes that devices priced under $250 cash-pay outperform reimbursed equivalents on actual adoption in eight of eleven markets studied.",
        "event_date": "2026-05-28",
        "source_url": "https://lanternhealth.fund/research/cash-pay-wins",
        "source_name": "Lantern Research \u2014 \"Cash-Pay Wins\"",
        "source_published_at": "2026-05-28",
        "confidence": 0.88,
        "verified_at": "2026-07-24T01:25:06.653273Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "priya@lanternhealthfund.com",
      "firm_domain": "www.fiercebiotech.com",
      "list_underfilled": true,
      "location": "Boston, MA",
      "check_min": 750000,
      "check_max": 2000000,
      "stage": [
        "Seed",
        "Series A"
      ],
      "sectors": [
        "Health Infra",
        "Accessibility"
      ],
      "score_breakdown": {
        "evidence_strength": 1.4519,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.806,
        "records": 3.0,
        "normalized": 0.9371,
        "affinity_tiebreak": 0.0
      },
      "draft_id": null
    },
    {
      "target_id": "9945e811-4619-41b1-be2c-dfbfe760f06b",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Kettle & Vane",
      "investor_person": "Tomas Berg",
      "role": "Partner",
      "score": 0.8634,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "c0fe98d7-d3cc-47c7-88d7-a8e720af0721",
          "investor_firm": "Kettle & Vane",
          "investor_person": "Tomas Berg",
          "kind": "thesis_publication",
          "claim": "Writes a recurring column on contract manufacturing for early hardware teams.",
          "detail": "June entry argues that seed hardware investors should underwrite the BOM, not the demo, and that most funds cannot read a cost sheet.",
          "event_date": "2026-06-06",
          "source_url": "https://kettlevane.com/notes/underwrite-the-bom",
          "source_name": "Kettle Notes \u2014 \"Underwrite the BOM\"",
          "source_published_at": "2026-06-06",
          "confidence": 0.84,
          "verified_at": "2026-07-24T01:25:06.653304Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "a2667b30-498a-40ef-a861-54fd30d930c6",
          "investor_firm": "Kettle & Vane",
          "investor_person": "Tomas Berg",
          "kind": "fund_close",
          "claim": "Kettle & Vane announced a \u20ac90M second fund and resumed deploying in May 2026.",
          "detail": "Paused new investments for eight months in 2025; the pause ended with the Fund II first close.",
          "event_date": "2026-05-04",
          "source_url": "https://kettlevane.com/fund-ii",
          "source_name": "Kettle & Vane \u2014 fund announcement",
          "source_published_at": "2026-05-04",
          "confidence": 0.74,
          "verified_at": "2026-07-24T01:25:06.653304Z",
          "stale": false,
          "intent_kind": "geo_crossing"
        },
        {
          "id": "7a3c7386-9b22-4d31-9c90-8f83bb5c96c4",
          "investor_firm": "Kettle & Vane",
          "investor_person": "Tomas Berg",
          "kind": "portfolio_investment",
          "claim": "Backed Fathom Instruments, a low-cost medical device manufacturer in Porto.",
          "detail": "Same manufacturing corridor Novi uses. Fathom proved the Iberian contract-manufacturing route to sub-$200 medical hardware.",
          "event_date": "2025-10-15",
          "source_url": "https://www.eu-startups.com/2025/10/fathom-instruments-seed",
          "source_name": "EU-Startups \u2014 Fathom Instruments seed",
          "source_published_at": "2025-10-15",
          "confidence": 0.8,
          "verified_at": "2026-07-24T01:25:06.653304Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "c0fe98d7-d3cc-47c7-88d7-a8e720af0721",
        "investor_firm": "Kettle & Vane",
        "investor_person": "Tomas Berg",
        "kind": "thesis_publication",
        "claim": "Writes a recurring column on contract manufacturing for early hardware teams.",
        "detail": "June entry argues that seed hardware investors should underwrite the BOM, not the demo, and that most funds cannot read a cost sheet.",
        "event_date": "2026-06-06",
        "source_url": "https://kettlevane.com/notes/underwrite-the-bom",
        "source_name": "Kettle Notes \u2014 \"Underwrite the BOM\"",
        "source_published_at": "2026-06-06",
        "confidence": 0.84,
        "verified_at": "2026-07-24T01:25:06.653304Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "tomas@kettlevane.com",
      "firm_domain": "www.eu-startups.com",
      "list_underfilled": true,
      "location": "Berlin, DE",
      "check_min": 400000,
      "check_max": 1200000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Hardware",
        "Supply Chain"
      ],
      "score_breakdown": {
        "evidence_strength": 1.3663,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.8344,
        "records": 3.0,
        "normalized": 0.8819,
        "affinity_tiebreak": 0.008
      },
      "draft_id": null
    },
    {
      "target_id": "dfdebe89-70d8-4b16-b632-3d4d58a39066",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Meridian Seed",
      "investor_person": "Daniel Okoro",
      "role": "Managing Partner",
      "score": 0.8513,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "4f74dc2a-2565-4b40-8617-5371e6bc208a",
          "investor_firm": "Meridian Seed",
          "investor_person": "Daniel Okoro",
          "kind": "thesis_publication",
          "claim": "Runs a public memo series on distribution-first hardware in emerging markets.",
          "detail": "March memo: the winning pattern is a device sold through existing pharmacy and telecom retail, not through clinical channels.",
          "event_date": "2026-03-27",
          "source_url": "https://meridianseed.com/memos/shelf-space-first",
          "source_name": "Meridian Memos \u2014 \"Shelf Space First\"",
          "source_published_at": "2026-03-27",
          "confidence": 0.82,
          "verified_at": "2026-07-24T01:25:06.653233Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "35b4b72e-e3d9-4ebe-8e47-617fe5aea93d",
          "investor_firm": "Meridian Seed",
          "investor_person": "Daniel Okoro",
          "kind": "fund_close",
          "claim": "Meridian is deploying from a $35M rolling vehicle with a two-week decision cycle.",
          "detail": "Publicly commits to a decision within ten business days of first call. Eleven checks year to date.",
          "event_date": "2026-06-01",
          "source_url": "https://meridianseed.com/how-we-invest",
          "source_name": "Meridian Seed \u2014 how we invest",
          "source_published_at": "2026-06-01",
          "confidence": 0.7,
          "verified_at": "2026-07-24T01:25:06.653233Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "51b99cad-9ceb-469d-b9ad-12cbed886b22",
          "investor_firm": "Meridian Seed",
          "investor_person": "Daniel Okoro",
          "kind": "portfolio_investment",
          "claim": "Backed Kiosk Health, which distributes diagnostics through pharmacy counters.",
          "detail": "Kiosk operates 1,900 pharmacy counters across three markets \u2014 the same shelf Novi needs for retail distribution.",
          "event_date": "2026-02-19",
          "source_url": "https://meridianseed.com/portfolio/kiosk-health",
          "source_name": "Meridian Seed \u2014 Kiosk Health announcement",
          "source_published_at": "2026-02-19",
          "confidence": 0.78,
          "verified_at": "2026-07-24T01:25:06.653233Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "4f74dc2a-2565-4b40-8617-5371e6bc208a",
        "investor_firm": "Meridian Seed",
        "investor_person": "Daniel Okoro",
        "kind": "thesis_publication",
        "claim": "Runs a public memo series on distribution-first hardware in emerging markets.",
        "detail": "March memo: the winning pattern is a device sold through existing pharmacy and telecom retail, not through clinical channels.",
        "event_date": "2026-03-27",
        "source_url": "https://meridianseed.com/memos/shelf-space-first",
        "source_name": "Meridian Memos \u2014 \"Shelf Space First\"",
        "source_published_at": "2026-03-27",
        "confidence": 0.82,
        "verified_at": "2026-07-24T01:25:06.653233Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "daniel@meridianseed.com",
      "firm_domain": "meridianseed.com",
      "list_underfilled": true,
      "location": "London, UK",
      "check_min": 150000,
      "check_max": 500000,
      "stage": [
        "Pre-Seed"
      ],
      "sectors": [
        "Consumer Tech",
        "Emerging Markets"
      ],
      "score_breakdown": {
        "evidence_strength": 1.3598,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.6348,
        "records": 3.0,
        "normalized": 0.8777,
        "affinity_tiebreak": 0.0
      },
      "draft_id": null
    },
    {
      "target_id": "62983e7f-2cb9-42ff-bd5d-3b79839ae77d",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Tidewater Group",
      "investor_person": "Hannah Vos",
      "role": "Partner",
      "score": 0.7974,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "ae108de7-a61d-42f0-8ac5-a69089f0b6b8",
          "investor_firm": "Tidewater Group",
          "investor_person": "Hannah Vos",
          "kind": "thesis_publication",
          "claim": "Told Bloomberg that European hardware seed rounds are structurally underpriced.",
          "detail": "Says Tidewater will write earlier checks than its mandate suggests when the manufacturing route is already proven.",
          "event_date": "2026-04-08",
          "source_url": "https://www.bloomberg.com/news/articles/2026-04-08/european-hardware-seed",
          "source_name": "Bloomberg \u2014 European hardware funding",
          "source_published_at": "2026-04-08",
          "confidence": 0.72,
          "verified_at": "2026-07-24T01:25:06.653262Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "201af75b-2a56-42a4-93d2-41d42f41c08e",
          "investor_firm": "Tidewater Group",
          "investor_person": "Hannah Vos",
          "kind": "portfolio_gap",
          "claim": "Tidewater has no consumer-facing medical device in the portfolio.",
          "detail": "Eleven industrial and component companies, zero consumer endpoints. Portfolio review published June 2026.",
          "event_date": "2026-06-15",
          "source_url": "https://tidewater.group/portfolio-review-2026",
          "source_name": "Tidewater Group \u2014 2026 portfolio review",
          "source_published_at": "2026-06-15",
          "confidence": 0.68,
          "verified_at": "2026-07-24T01:25:06.653262Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "064d8eb4-54a2-46d1-b737-3cc3154c4dcc",
          "investor_firm": "Tidewater Group",
          "investor_person": "Hannah Vos",
          "kind": "portfolio_investment",
          "claim": "Led a Series A in Verge Robotics, a Portuguese precision-assembly company.",
          "detail": "\u20ac8M round, December 2025. Verge assembles the exact class of miniature transducer housing Novi ships in volume.",
          "event_date": "2025-12-04",
          "source_url": "https://tidewater.group/news/verge-robotics-series-a",
          "source_name": "Tidewater Group \u2014 Verge Robotics Series A",
          "source_published_at": "2025-12-04",
          "confidence": 0.8,
          "verified_at": "2026-07-24T01:25:06.653262Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "ae108de7-a61d-42f0-8ac5-a69089f0b6b8",
        "investor_firm": "Tidewater Group",
        "investor_person": "Hannah Vos",
        "kind": "thesis_publication",
        "claim": "Told Bloomberg that European hardware seed rounds are structurally underpriced.",
        "detail": "Says Tidewater will write earlier checks than its mandate suggests when the manufacturing route is already proven.",
        "event_date": "2026-04-08",
        "source_url": "https://www.bloomberg.com/news/articles/2026-04-08/european-hardware-seed",
        "source_name": "Bloomberg \u2014 European hardware funding",
        "source_published_at": "2026-04-08",
        "confidence": 0.72,
        "verified_at": "2026-07-24T01:25:06.653262Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "hannah@tidewatergroup.com",
      "firm_domain": "tidewater.group",
      "list_underfilled": true,
      "location": "Amsterdam, NL",
      "check_min": 1000000,
      "check_max": 3000000,
      "stage": [
        "Seed",
        "Series A"
      ],
      "sectors": [
        "Hardware",
        "Manufacturing"
      ],
      "score_breakdown": {
        "evidence_strength": 1.2609,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.6649,
        "records": 3.0,
        "normalized": 0.8138,
        "affinity_tiebreak": 0.008
      },
      "draft_id": null
    },
    {
      "target_id": "b83ba536-ca57-4466-a5e6-1d87cbd5200c",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Resonance Partners",
      "investor_person": "Sarah Jenkins",
      "role": "Founding Partner",
      "score": 0.744,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "0993e942-20cb-4440-bae3-f9fa8303616a",
          "investor_firm": "Resonance Partners",
          "investor_person": "Sarah Jenkins",
          "kind": "portfolio_investment",
          "claim": "Backed Cadence Health, a remote hearing-test provider, at pre-seed.",
          "detail": "Cadence routes diagnosed users to devices it does not make. The referral path into a low-cost device is unbuilt on both sides.",
          "event_date": "2026-04-30",
          "source_url": "https://resonance.partners/portfolio/cadence-health",
          "source_name": "Resonance Partners \u2014 portfolio note",
          "source_published_at": "2026-04-30",
          "confidence": 0.79,
          "verified_at": "2026-07-24T01:25:06.653063Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "ef2e5a0a-d14d-4821-ac00-b1a13209a675",
          "investor_firm": "Resonance Partners",
          "investor_person": "Sarah Jenkins",
          "kind": "thesis_publication",
          "claim": "Keynoted \"The Next Decade of Wearable Audio\" at TechCrunch Disrupt.",
          "detail": "Twelve minutes of the talk are about manufacturing cost curves in bone conduction and why the category stalled at premium price points.",
          "event_date": "2025-11-18",
          "source_url": "https://techcrunch.com/video/disrupt-2025-wearable-audio",
          "source_name": "TechCrunch Disrupt 2025 \u2014 session recording",
          "source_published_at": "2025-11-18",
          "confidence": 0.91,
          "verified_at": "2026-07-24T01:25:06.653063Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "3394b767-ec91-4979-82d4-f4d9ccef57c1",
          "investor_firm": "Resonance Partners",
          "investor_person": "Sarah Jenkins",
          "kind": "fund_close",
          "claim": "Resonance closed a $60M debut fund dedicated to audio and acoustics.",
          "detail": "Single-sector fund, first close January 2026. Nine of the first twelve checks went to hardware companies rather than software.",
          "event_date": "2026-01-09",
          "source_url": "https://axios.com/pro-rata/resonance-partners-fund-i",
          "source_name": "Axios Pro Rata \u2014 Resonance debut fund",
          "source_published_at": "2026-01-09",
          "confidence": 0.83,
          "verified_at": "2026-07-24T01:25:06.653063Z",
          "stale": true,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "0993e942-20cb-4440-bae3-f9fa8303616a",
        "investor_firm": "Resonance Partners",
        "investor_person": "Sarah Jenkins",
        "kind": "portfolio_investment",
        "claim": "Backed Cadence Health, a remote hearing-test provider, at pre-seed.",
        "detail": "Cadence routes diagnosed users to devices it does not make. The referral path into a low-cost device is unbuilt on both sides.",
        "event_date": "2026-04-30",
        "source_url": "https://resonance.partners/portfolio/cadence-health",
        "source_name": "Resonance Partners \u2014 portfolio note",
        "source_published_at": "2026-04-30",
        "confidence": 0.79,
        "verified_at": "2026-07-24T01:25:06.653063Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "sarah@resonancepartners.com",
      "firm_domain": "techcrunch.com",
      "list_underfilled": true,
      "location": "Austin, TX",
      "check_min": 250000,
      "check_max": 1000000,
      "stage": [
        "Pre-Seed",
        "Seed"
      ],
      "sectors": [
        "Audio Hardware"
      ],
      "score_breakdown": {
        "evidence_strength": 1.1884,
        "breadth_multiplier": 1.12,
        "lead_recency": 0.7236,
        "records": 3.0,
        "normalized": 0.767,
        "affinity_tiebreak": 0.0
      },
      "draft_id": null
    },
    {
      "target_id": "1de73ed7-5b6a-4ee8-9815-eb2a09940a10",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "investor_firm": "Halden Ventures",
      "investor_person": "Lena Fischer",
      "role": "Investment Partner",
      "score": 0.5289,
      "status": "new",
      "notes": null,
      "evidence": [
        {
          "id": "776007a7-ae47-4b05-9abc-c6b003885e12",
          "investor_firm": "Halden Ventures",
          "investor_person": "Lena Fischer",
          "kind": "thesis_publication",
          "claim": "Wrote that assistive devices are the highest-leverage health category per euro deployed.",
          "detail": "Quantifies cost per disability-adjusted life year for hearing devices at roughly a fifth of comparable interventions.",
          "event_date": "2026-05-02",
          "source_url": "https://haldenventures.com/journal/leverage-per-euro",
          "source_name": "Halden Journal \u2014 \"Leverage per Euro\"",
          "source_published_at": "2026-05-02",
          "confidence": 0.73,
          "verified_at": "2026-07-24T01:25:06.653283Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        },
        {
          "id": "e4d2a689-f8cb-4c2b-8579-98a47ad772d7",
          "investor_firm": "Halden Ventures",
          "investor_person": "Lena Fischer",
          "kind": "fund_close",
          "claim": "Halden closed a \u20ac120M fund with a mandate for global-south health distribution.",
          "detail": "LP base includes two development finance institutions requiring deployment outside Western Europe.",
          "event_date": "2026-03-16",
          "source_url": "https://haldenventures.com/fund-iii",
          "source_name": "Halden Ventures \u2014 Fund III close",
          "source_published_at": "2026-03-16",
          "confidence": 0.76,
          "verified_at": "2026-07-24T01:25:06.653283Z",
          "stale": false,
          "intent_kind": "adjacent_portfolio"
        }
      ],
      "lead_evidence": {
        "id": "776007a7-ae47-4b05-9abc-c6b003885e12",
        "investor_firm": "Halden Ventures",
        "investor_person": "Lena Fischer",
        "kind": "thesis_publication",
        "claim": "Wrote that assistive devices are the highest-leverage health category per euro deployed.",
        "detail": "Quantifies cost per disability-adjusted life year for hearing devices at roughly a fifth of comparable interventions.",
        "event_date": "2026-05-02",
        "source_url": "https://haldenventures.com/journal/leverage-per-euro",
        "source_name": "Halden Journal \u2014 \"Leverage per Euro\"",
        "source_published_at": "2026-05-02",
        "confidence": 0.73,
        "verified_at": "2026-07-24T01:25:06.653283Z",
        "stale": false,
        "intent_kind": "adjacent_portfolio"
      },
      "contact_email": "lena@haldenventures.com",
      "firm_domain": "haldenventures.com",
      "list_underfilled": true,
      "location": "Copenhagen, DK",
      "check_min": 300000,
      "check_max": 900000,
      "stage": [
        "Seed"
      ],
      "sectors": [
        "Health Infra",
        "Emerging Markets"
      ],
      "score_breakdown": {
        "evidence_strength": 0.8792,
        "breadth_multiplier": 1.06,
        "lead_recency": 0.7292,
        "records": 2.0,
        "normalized": 0.5371,
        "affinity_tiebreak": 0.008
      },
      "draft_id": null
    }
  ],
  "drafts": [
    {
      "draft_id": "6be8383c-d203-4b66-a9ac-f9a5b2d5e0ec",
      "target_id": "bed0f710-a81a-4295-ac90-30136ef048a6",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, April 2026 thesis",
      "body": "Elias,\n\nYou argued on the Northbound podcast that hearables are the next platform shift after the watch in April 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nOverture holds three audio-adjacent companies and none in hearing assistance \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Worth twenty minutes?\n\n\u2014 Ines",
      "word_count": 89,
      "lead_evidence_id": "7e5aac81-9a93-43c9-9a9f-d50d0d679648",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": "No prior thread \u2014 0 messages in your mailbox."
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.898580Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "fc46ca1a-4ed8-4f3e-90b6-9efa89a0205c",
      "target_id": "96516b0c-87c2-4539-a4c3-c2e197ea0e27",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, May 2026 thesis",
      "body": "Maya,\n\nYou published a thesis on overlooked hearing infrastructure and accessibility markets in May 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nThe check we are looking for sits inside your $300K\u2013$800K range.\n\n78% retention at day 90 is the number I would want you to push on.\n\nWe are raising $3.5M. Worth twenty minutes?\n\n\u2014 Ines",
      "word_count": 90,
      "lead_evidence_id": "f51b6606-8d7d-4c80-9a0c-08a0789cb510",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": null
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.900389Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "95af23c5-1b86-4d9c-a7ba-583dfc8d8ef8",
      "target_id": "a687b5ad-e9e3-4497-bb43-ffa813e0c634",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "The bone conduction hole in the Foundry Line portfolio",
      "body": "Marcus,\n\nYour accessibility track has no hearing company after five months, as of July 2026. We are what goes in that hole.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nYou opened an accessibility-focused investment track after a public commitment in February \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Open to a short call this week?\n\n\u2014 Ines",
      "word_count": 90,
      "lead_evidence_id": "8a1fcedc-b667-4c15-a103-3fad007372aa",
      "prior_contact": {
        "found": true,
        "last_thread_at": "2026-06-05",
        "summary": "Two prior threads \u2014 intro attempted via a shared portfolio founder in January 2026."
      },
      "blockers": [
        "prior_contact_exists"
      ],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.901561Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "3925d60b-22dd-403b-803f-adbbea29b9df",
      "target_id": "c60f03db-a5af-4fb6-8455-ff37181782f9",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, May 2026 thesis",
      "body": "Priya,\n\nYou published research on reimbursement-free medical devices in emerging markets in May 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nLantern holds seven accessibility companies, all software \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Can I send the trial data?\n\n\u2014 Ines",
      "word_count": 83,
      "lead_evidence_id": "3972062c-ae56-49fa-8526-235e62406b20",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": null
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.902524Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "706cb7eb-c113-4892-95d7-d8755cfe0efa",
      "target_id": "9945e811-4619-41b1-be2c-dfbfe760f06b",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, June 2026 thesis",
      "body": "Tomas,\n\nYou write a recurring column on contract manufacturing for early hardware teams in June 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nKettle & Vane announced a \u20ac90M second fund and resumed deploying in May 2026 \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Can I send the trial data?\n\n\u2014 Ines",
      "word_count": 92,
      "lead_evidence_id": "c0fe98d7-d3cc-47c7-88d7-a8e720af0721",
      "prior_contact": {
        "found": true,
        "last_thread_at": "2026-07-02",
        "summary": "One prior thread \u2014 you emailed the firm's general address in March 2026, no reply."
      },
      "blockers": [
        "prior_contact_exists"
      ],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.905610Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "63fe11eb-23a3-4339-beaa-0d0b389d0629",
      "target_id": "dfdebe89-70d8-4b16-b632-3d4d58a39066",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, March 2026 thesis",
      "body": "Daniel,\n\nYou run a public memo series on distribution-first hardware in emerging markets in March 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nMeridian is deploying from a $35M rolling vehicle with a two-week decision cycle \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Open to a short call this week?\n\n\u2014 Ines",
      "word_count": 92,
      "lead_evidence_id": "4f74dc2a-2565-4b40-8617-5371e6bc208a",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": null
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.907721Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "6db3e3ef-c98c-486b-99ee-4d8abd4bb472",
      "target_id": "62983e7f-2cb9-42ff-bd5d-3b79839ae77d",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, April 2026 thesis",
      "body": "Hannah,\n\nYou told Bloomberg that European hardware seed rounds are structurally underpriced in April 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nTidewater has no consumer-facing medical device in the portfolio \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Can I send the trial data?\n\n\u2014 Ines",
      "word_count": 86,
      "lead_evidence_id": "ae108de7-a61d-42f0-8ac5-a69089f0b6b8",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": null
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.908565Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "f507fe95-7717-4050-8438-566c9371f2b7",
      "target_id": "b83ba536-ca57-4466-a5e6-1d87cbd5200c",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Adjacent to your Resonance Partners portfolio \u2014 Novi Audio",
      "body": "Sarah,\n\nYou backed Cadence Health, a remote hearing-test provider, at pre-seed in April 2026. We sit one step from that, not against it.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nYou keynoted \"The Next Decade of Wearable Audio\" at TechCrunch Disrupt \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Can I send the trial data?\n\n\u2014 Ines",
      "word_count": 89,
      "lead_evidence_id": "0993e942-20cb-4440-bae3-f9fa8303616a",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": null
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.909426Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    },
    {
      "draft_id": "3ceda62f-4e76-47d0-9f17-836c4a13bc21",
      "target_id": "1de73ed7-5b6a-4ee8-9815-eb2a09940a10",
      "run_id": "b8d5e45f-2b2e-467c-82f6-e993d5f3ec57",
      "subject": "Bone conduction \u2014 Novi Audio seed, May 2026 thesis",
      "body": "Lena,\n\nYou wrote that assistive devices are the highest-leverage health category per euro deployed in May 2026. That argument is the company we built.\n\nNovi Audio: Bone-conduction hearing hardware for the 1.5B people priced out of clinical audiology. Today that is a $180 bill of materials, 240 users in Lisbon field trials, 78% retention at day 90.\n\nHalden closed a \u20ac120M fund with a mandate for global-south health distribution \u2014 happy to show you where the two actually connect.\n\nWe are raising $3.5M. Worth twenty minutes?\n\n\u2014 Ines",
      "word_count": 88,
      "lead_evidence_id": "776007a7-ae47-4b05-9abc-c6b003885e12",
      "prior_contact": {
        "found": false,
        "last_thread_at": null,
        "summary": null
      },
      "blockers": [],
      "version": 1,
      "updated_at": "2026-07-24T01:25:55.911529Z",
      "approved_at": null,
      "approved_by": null,
      "generated_by": "deterministic"
    }
  ]
}

export const offlineSnapshot = snapshot as unknown as {
  run: RunStatus
  rows: TargetSummary[]
  details: TargetDetail[]
  drafts: DraftPublic[]
}
