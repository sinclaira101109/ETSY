# Reusable Codex Prompts

Use these prompts in the Codex project. Keep the first run read-only.

## 1. Repository orientation
Read `AGENTS.md`, `README.md`, `docs/automation-roadmap.md`, and `config/workflow.example.yaml`. Inspect the repository and report what exists, what is missing, and any conflicts. Do not change files.

## 2. Product data audit
Inspect only the product files I explicitly place in `data/inbox/`. Preserve originals. Build a SKU-level data-quality report with source references and mark every unknown field as `NEEDS_CONFIRMATION`. Do not infer prices, dimensions, materials, lead times, MOQ, certifications, or delivery guarantees.

## 3. Etsy listing review
For the selected SKUs, audit title, tags, description, attributes, and photo sequence. Separate consumer search intent from B2B procurement terms. Provide a before/after recommendation table and copy-ready drafts. Do not publish or modify live Etsy listings.

## 4. B2B prospecting preparation
For the selected products, propose buyer segments, search terms, company qualification criteria, and personalized outreach drafts. Do not spend lead credits, export prospect personal data, or send email. Include an opt-out line and note that any legal requirements must be checked for the target market.

## 5. Verify a completed phase
Compare the output with the acceptance criteria in `docs/automation-roadmap.md`. Check for unsupported claims, duplicate or mismatched keywords, missing source references, secret leakage, and accidental source-file changes. Report checks performed and unresolved risks.

## 6. Prepare a scheduled task
First describe exactly what the task will read, create, and not touch. It must only produce a dated report/drafts, never publish listings, send emails, spend credits, or change prices. Ask for approval before enabling a schedule.
