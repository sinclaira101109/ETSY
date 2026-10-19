# Codex Workflow Roadmap

## Goal
Reduce repetitive Etsy and B2B operations while keeping factual accuracy, account security, and human approval at the center.

## Phase 0 — Project baseline
- Read `AGENTS.md` and inventory current files.
- Define one canonical product record per SKU.
- Separate public product facts from internal cost/pricing data.
- Keep secrets and private customer data outside Git.

Acceptance: every product has a source file, SKU, verified title/name, material, dimensions, included items, production time, shipping estimate, and fields marked unknown when not confirmed.

## Phase 1 — Product data quality
Inputs: copied product spreadsheets, supplier facts, photos, and existing listing exports.
Tasks:
- Identify duplicate SKUs and inconsistent specifications.
- Flag missing dimensions, materials, included/excluded accessories, MOQ, wholesale prices, and production lead time.
- Preserve original files and create a data-quality report.
Output: a normalized catalog draft plus a list of questions requiring owner confirmation.

Acceptance: no unknown field is silently guessed; source references are recorded.

## Phase 2 — Etsy listing audit and draft generation
Tasks:
- Review title, 13 tags, description, attributes, photo order, and buyer objections for each selected listing.
- Check title/tag intent alignment and avoid keyword stuffing.
- Separate consumer search terms from wholesale buyer-search terms.
- Draft optimized listing copy and image shot lists.
Output: per-SKU recommendations and copy-ready drafts.

Approval gate: no listing is published or edited automatically.

## Phase 3 — LeadPilot B2B prospecting preparation
Tasks:
- Generate search groups by buyer type: gift retailers, gift distributors, florists, wedding/event suppliers, corporate gifting companies, and baby-gift retailers where relevant.
- Prepare company qualification criteria and personalized email drafts.
- Track prospect source, country, buyer type, product fit, contact status, response, next action, and opt-out status.
- Deduplicate prospects and honor suppression lists.

Approval gate: do not spend LeadPilot credits or send outreach automatically in the initial version.

## Phase 4 — Reporting
Create a weekly report showing:
- New/updated SKUs reviewed
- Missing or conflicting product facts
- Listings needing action
- Search terms and buyer segments tested
- Prospects qualified and draft emails prepared
- Follow-ups due
- Decisions needed from the owner

Acceptance: every recommendation links to its source and has a clear next action.

## Phase 5 — Integrations and scheduling
Only after Phases 1–4 pass manual validation:
- Add local scheduled tasks or GitHub Actions for non-sensitive report generation.
- Add approved connectors/API integrations only when official supported access and credentials are available.
- Store credentials in local environment variables or repository secrets, never in code or committed files.
- Add logs, retry limits, error notifications, and a disable switch.

Do not automate browser clicks against live Etsy/LeadPilot pages as a substitute for an approved API or integration. Do not bypass platform protections.

## Recommended first pilot
Use one shop and 5–10 SKUs. Run one manual cycle end-to-end:
1. Import product data.
2. Produce a data-quality report.
3. Audit listing SEO and photos.
4. Draft B2B prospecting groups and 3-email sequences.
5. Review the outputs.
6. Record corrections and only then decide what should run on a schedule.
