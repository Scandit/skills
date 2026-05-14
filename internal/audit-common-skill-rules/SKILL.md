---
name: audit-common-skill-rules
description: Use when the user wants to verify that the universal trust-and-verification rules are present in every Scandit SDK skill in this repo. Triggered by "audit common skill rules", "check rule consistency across skills", or "audit skills for missing trust rules".
license: MIT
metadata:
  author: scandit
  version: "3.1.0"
---

# Audit Common Rules

Walks every `skills/*/SKILL.md` and reports which ones are missing required content. Read-only — never edit files.

Wording may vary per product and platform (e.g. `SparkScan API` vs `BarcodeCapture API`; `view modifiers` on iOS vs `plugin names` on Capacitor). The audit checks whether each required rule is **conveyed**, not that it matches verbatim.

## How to run

1. List every `skills/*/SKILL.md`, skipping `skills/audit-common-rules/`, any `skills/_*` directory, and the per-section exempts below.
2. For each skill, check whether each required H2 exists and conveys every required rule.
3. Output a report:
   - **Compliant:** list of skill names.
   - **Issues:** one row per problem — `<skill> · <section> · <short label> · <one-line hint>`. The `<short label>` is either `MISSING_SECTION` or a short paraphrase of the missing rule (e.g. `missing "fetch-when-missing"`). Group identical issues across many skills into a single row with a skill list.
   - **Totals.**

## Required content

### 1. `## Critical: Do Not Trust Internal Knowledge`

Must exist and convey:

- Training data may contain outdated or incorrect Scandit SDK APIs.
- Always verify APIs against the references in this skill before writing or suggesting code.
- Do not rely on memorized method signatures, parameters, or platform-specific surface terms.

_Exempt: `data-capture-sdk` (advisory skill, different trust rule)._

### 2. `## API Usage Policy`

Must exist and convey:

- Only use APIs documented in this skill's references.
- Do not invent or guess method signatures or parameters.
- Fetch the relevant reference page when unsure or on a compile error.
- Do not tell the user to check the docs themselves.
- Always include the relevant link in the answer.
- Never construct or guess documentation URLs — first check a fetched page for a direct hyperlink, otherwise fetch the API index and extract the real link.

_Exempt: `data-capture-sdk`._
