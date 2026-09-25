# Product Decision Guide

Follow this qualification flow when helping a user choose a Scandit product. Ask questions in order and stop as soon as you can make a confident recommendation.

**Keep it conversational.** Ask one or two questions at a time — do not present all options upfront. If the user's request is vague, start by asking them to describe their task or workflow in their own words rather than presenting technical categories they may not be familiar with.

**Confidence shortcut.** If the user's description already contains enough detail to confidently match a Q5 workflow (count-and-verify, search-and-find, batch capture, or custom AR overlays), skip Q1–Q4 and go directly to the product recommendation. Then ask Q6 (platform) to provide the right docs and sample links. Examples of clear signals:
- "count inventory and compare against a manifest/expected list" → MatrixScan Count
- "find/locate a specific item among many", "highlight the right package" → MatrixScan Find
- "scan all barcodes into a list", "proof of delivery batch" → MatrixScan Batch
- "overlay custom info on each barcode", "show price/expiry on each item" → MatrixScan AR

When the workflow could plausibly match more than one Q5 product, ask one targeted clarifying question to disambiguate rather than guessing. For example, high-volume receiving could be either MatrixScan Batch (capture all barcodes into a list) or MatrixScan Count (scan and verify against a manifest) — ask whether they need to verify scanned items against an expected shipment list, or just capture everything as fast as possible. One question is enough to resolve the ambiguity; don't over-qualify beyond that.

Only fall back to Q1–Q4 when the request is genuinely ambiguous or could match multiple products.

## Qualification Flow

### Q0: Can you describe what you're trying to do?

If the user's request is vague (e.g., "I need scanning"), start here. Ask them to describe the task or workflow — e.g., "Could you tell me a bit about what the scanning is for? What's the task the user will be performing?" Their answer will often let you skip directly to the right product without needing to ask all the technical questions below.

### Q1: Can you modify your application code, or do you need to add scanning without code changes?

- **Cannot modify existing app / no development resources / needs to work with an unmodifiable system** → **Scandit Express**. Explain that Express provides the same Scandit scanning capabilities (inventory count, find items, scan labels, read IDs) as a standalone app that injects data into their existing system via keyboard wedge, intents, or web app connection. Continue the conversation to understand which workflow they need, then point them to Express docs.
- **Building a new app or can modify existing code** → Continue to Q2.

### Q2: What do you need to scan?

- **Identity documents** (passports, driver's licenses, ID cards) → **ID Capture**. Skip to Q6.
- **Text on labels** (OCR — expiry dates, lot numbers, serial numbers alongside barcodes) → **Smart Label Capture**. Skip to Q6.
- **Barcodes only** → Continue to Q3.

### Q3: Do you need to scan a single barcode at a time, or multiple barcodes simultaneously?

- **Single barcode** → Continue to Q4.
- **Multiple barcodes** → Continue to Q5.

### Q4: Do you need full control over the scanning UI, or would a pre-built experience work?

Both SparkScan and Barcode Capture use the exact same scanning engine — same symbologies, same AI features, same performance. The choice is purely about UI:

- **Pre-built UI, fast integration** → **SparkScan**. Its UI has been refined through extensive customer and user testing to optimize ergonomics and usability. Less integration effort, polished out-of-the-box experience. Skip to Q6.
- **Full custom UI, maximum flexibility** → **Barcode Capture**. You build the entire scanning experience yourself — complete freedom over look, feel, and behavior. Skip to Q6.

### Q5: What best describes the workflow?

- **Capture all barcodes at once** into a list (proof of delivery, high-volume receiving, inventory counting, packing) → **MatrixScan Batch (BarcodeBatch)**.
- **Display custom AR overlays** with dynamic information on each item (stock levels, sorting instructions, interactive experiences) → **MatrixScan AR**.
- **Count items and verify against an expected list** (inventory count, receiving verification, stock take) → **MatrixScan Count (BarcodeCount)**. This is a specialized workflow product — recommend the user contact Scandit support at https://support.scandit.com to confirm it fits their use case. If they want to start integrating, point them to the sample app as the reference implementation.
- **Find a specific item** among many (order picking, locate a package on a shelf) → **MatrixScan Find (BarcodeFind)**. This is a specialized workflow product — recommend the user contact Scandit support at https://support.scandit.com to confirm it fits their use case. If they want to start integrating, point them to the sample app as the reference implementation.

### Q6: What platform are you targeting?

Ask this once a product is identified. Then check the product catalog for platform availability and either:
- Hand off to the appropriate implementation skill (see Handoff Table in SKILL.md), or
- Provide the docs.scandit.com link and sample repository for the target platform.

---

## Disambiguation Rules

- **Vague "scan barcodes"**: Do NOT assume a product. Ask Q3 and Q4 first.
- **"MatrixScan"**: Clarify which variant — Batch (list capture), AR (custom overlays), Count (counting with verification), or Find (locate specific items).
- **"AR" or "augmented reality"**: Explore whether they need Find (search), or custom AR overlays (MatrixScan AR).
- **"OCR" or "text recognition" or "read labels"**: The answer is always **Smart Label Capture** — it is the only Scandit product with OCR.
- **Renamed products**: If the user says "BarcodeBatch", "BarcodeFind", or "BarcodeCount", confirm they mean the same as the legacy MatrixScan name and proceed.
- **Combined needs**: If the user needs both single scanning and multi-barcode workflows, recommend SparkScan as the entry point — it has built-in buttons to switch to advanced modes like Smart Label Capture.
- **Image analysis**: If the user shares an image of barcodes or labels, use it to inform your recommendation:
  - Dense barcodes on a shelf or pallet → BarcodeBatch or MatrixScan AR depending on workflow.
  - A label with text and barcodes → Smart Label Capture.
  - A single barcode on an item → single scanning (SparkScan or Barcode Capture).

---

## Presenting the Recommendation

1. **Identify one to two best-fit products** based on collected information.
2. **Present in a comparison format** if two options are viable — explain your primary recommendation and the alternative, highlighting key trade-offs.
3. **Once the user confirms**, provide: product name, rationale, integration path (pre-built component, custom SDK, or no-code), and the recommended next step (docs link, skill handoff, or sample app).
