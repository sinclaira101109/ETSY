# Codex Operating Instructions

## Project purpose
Build a reliable, human-supervised operations workflow for the user's Etsy businesses, initially covering:
- Etsy listing research and SEO drafts
- Product catalog and pricing-file analysis
- Product-photo review checklists
- LeadPilot B2B prospecting preparation and outreach drafts
- Weekly operations reports and prioritized task lists

## Working rules
1. Inspect existing files and current project conventions before changing anything.
2. Treat product spreadsheets, screenshots, supplier descriptions, and shop data as source material. Do not invent product specifications, certifications, stock, production capacity, prices, customer history, or delivery guarantees.
3. Keep Etsy consumer SEO separate from B2B buyer-search terms.
4. Do not publish or edit live Etsy listings, send outreach emails, buy leads/credits, change prices, or contact prospects without explicit human approval for that specific action.
5. Start with read-only analysis and drafts. Any external write action must be gated by a review step and a clear confirmation.
6. Preserve original input files. Write generated reports to dated output folders; never overwrite source spreadsheets or photos.
7. Track assumptions, missing data, sources, and confidence. Mark unknown values as NEEDS_CONFIRMATION.
8. Use natural American English for US-facing copy; avoid unsupported superlatives, fake urgency, and generic AI-sounding language.
9. For B2B outreach, include a truthful sender identity and an appropriate opt-out line; respect suppression lists and applicable laws.
10. Never put passwords, API keys, email app passwords, tokens, or customer personal data in source control or logs. Use environment variables/secrets for credentials.
11. After changes, summarize files changed, checks run, unresolved risks, and the next human action.

## Default workflow
1. Inventory input files and identify the exact shop/product scope.
2. Validate data and identify missing fields.
3. Analyze and draft.
4. Run checks for factual consistency, duplicate tags, title/tag alignment, and unsupported claims.
5. Produce a report and draft outputs.
6. Pause for human review before any publishing, sending, pricing, or account changes.

## Definition of done
A task is complete only when outputs are saved, assumptions are explicit, checks are reported, and no external action has been taken without approval.
