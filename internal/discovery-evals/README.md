# Skill discovery and reference-loading pilot

We kept the original eight skill descriptions. The experimental descriptions helped Claude route tasks, but a lower-cost Codex model skipped the Android migration guide and gave incorrect advice on both attempts. Sonnet also consumed more total input with the candidate. The proposed descriptions remain in `candidate.json` for reproduction.

The product changes are a project-local selective-install example in the repository README and smaller, directly linked React Native MatrixScan Count references. The full plugin still exposes the entire catalog.

## Discovery

The five frozen tasks cover native Android integration, product selection, migration, unrelated QR generation and a React Native project containing an Android directory. Each session received a fresh project and one natural prompt. We scored observed skill use separately from final-answer correctness using the [frozen rubric](rubric.md). A quality pass requires all criteria for that task. A correct answer can pass quality even if the assistant never opened the required guidance.

| Harness and model | Correct route / 5, original → candidate | Task quality / 5 | Total session input across five tasks | Median first-call input |
| --- | --- | --- | ---: | ---: |
| Claude Code · Haiku 5.5 | 4 → 5 | 5 → 5 | 465,639 → 425,197 | 18,752 → 18,699 |
| Claude Code · Sonnet 5.5 | 3 → 5 | 4 → 5 | 261,741 → 362,160 | 17,928 → 17,877 |
| Codex · gpt-6-luna | 3 → 2 | 2 → 2 | 332,678 → 282,866 | unavailable |
| Codex · gpt-6.2-sol | 5 → 5 | 4 → 4 | 494,416 → 492,983 | unavailable |

The four configurations and tiers were selected before the trials. Claude Code 2.1.330 reported `claude-haiku-5-5` and `claude-sonnet-5-5`. Its catalog listed ordinary input/output prices of $0.10/$0.50 and $2/$10 per million tokens respectively at measurement time. Codex CLI 0.171.0 used the explicitly requested models at low effort. Its catalog identified Luna as the affordable option and Sol as the standard model. Its usage events did not pin a backend snapshot or report first-request usage. These input totals include cache reads and, where reported separately, cache writes. They measure the whole session, including follow-up tool turns. They are not invoices.

Each full package exposed 87 Scandit skills. Claude used a local plugin directory and reported three additional built-ins. Codex used project-local installation and reported four built-ins. We also inspected Codex's offline local marketplace installation. Even with the same skills present, the rendered project-local Scandit catalog occupied 20,759 → 20,757 characters for Luna and 38,409 → 38,327 for Sol. Luna's candidate Android entry cut off at “For React Native”, before the target skill name. The offline marketplace equivalents were 20,705 → 20,713 and 38,353 → 38,286 characters. These are character counts for catalog rows, independent of the session input totals.

On migration, Luna's candidate answer dropped the existing factory and the video-resolution deprecation. Its repeat again missed all three migration criteria. On Sonnet the baseline product-selection and React Native routing misses recurred. On Haiku a baseline Android-first detour did not recur. We preserved the first trial in every headline result and recorded diagnostic repeats separately. Single task pairs and targeted repeats do not establish population-wide rates. The decision required lower total input and preserved correctness on every configuration, including correct advisor and React Native routing. The candidate missed that threshold.

The [Claude initial scores](results/claude-discovery-initial.csv), [Claude repeats](results/claude-discovery-repeat1.csv) and [Codex observations](results/codex.json) record criterion outcomes, tool evidence and reported token components.

## React Native MatrixScan Count

We retained the original setup, camera lifecycle and navigation guidance together. Toolbar customization and capture-list mode each have a separate reference linked from the skill. We evaluated the original integration and toolbar tasks from `evals/matrixscan-count-rn/integration-evals.json`, using the same prompts, project inputs and assertion sets on each side. Counts below describe file content returned to the model. A partial read counts only its returned content. Some Claude searches lacked retained result text, so their totals are lower bounds.

| Model | Setup assertions / 20 | Setup reference tokens | Toolbar assertions / 6 | Toolbar reference tokens |
| --- | --- | ---: | --- | ---: |
| Haiku | 19 → 20 | 12,097 → 9,760 | 6 → 6 | 0 → 2,190 |
| Sonnet | 19 → 20 | 16,285 → 9,760 | 6 → 6 | 517 → 2,190 |
| Luna | 18 → 19 | 16,285 → 9,760 | 1 → 2 | 0 → 0 |
| Sol | 17 → 17 | 16,285 → 10,016 | 6 → 6 | 1,360 → 2,190 |

Setup reference consumption fell in every configuration. Natural toolbar tasks did not consistently open the guide. Luna skipped it in both variants and removed the existing camera-off exit handler. We then ran a separate [controlled toolbar experiment](controlled-toolbar.md) with an explicit instruction to use the installed skill and read its applicable reference. The controlled pairs measure the effect of the split when the guide is used. The natural trials above include discovery failures.

All four models passed all six toolbar assertions on both controlled variants, including preservation of the existing camera lifecycle. Haiku and Sonnet each went from 12,097 reference tokens to 2,190 (82% less). Luna went from 19,184 to 2,190 (89% less). Sol used a targeted search and a short excerpt on the original, so its 1,770 tokens rose to 2,190 (24% more). All eight controlled sessions returned measurable content. Reference counts use the same o200k_base tokenizer across harnesses and include repeated reads. The [guide results](results/guides.json) contain the per-assertion scores and per-opening counts.

## Reproduction

From the repository root at the pilot revision, use Python 3.9+ with PyYAML 6.x and authenticated native CLIs for the model trials. Each matrix command creates its own new output directory. Staging checks the package hashes below before running model sessions. The focused trials read their original prompts and screen fixtures from the baseline commit, which must be available locally. The stage and validator run offline.

The Codex project-local inventory check renders with a clean profile and the authenticated profile's cached model metadata when available. An offline rerun on Luna found the same 87 Scandit and four system skills. Its original-package catalog occupied 20,695 characters, compared with 20,759 in the trial.

```sh
python3 internal/discovery-evals/run.py stage --out /tmp/scandit-packages
python3 internal/discovery-evals/validate.py /tmp/scandit-packages/baseline
python3 internal/discovery-evals/validate.py /tmp/scandit-packages/candidate
python3 -m unittest discover -s internal/discovery-evals -p test_validate.py
python3 internal/discovery-evals/run.py matrix --out /tmp/scandit-discovery
python3 internal/discovery-evals/run.py guide-matrix --out /tmp/scandit-guides
python3 internal/discovery-evals/run.py controlled-toolbar --out /tmp/scandit-toolbar
```

Staging archives the publish allowlist from `5fc47c9f1e51b04237864c8b65026dc2665cd822`. It applies the Linux frontmatter correction from PR #153 identically before creating the comparison packages. The original unquoted description fails safe YAML parsing at `skills/scandit-linux-sdk/SKILL.md:3:77`. The regression fixture preserves that failure. All 87 corrected headers pass. The experimental package changes only eight descriptions. The guide-split package starts from the corrected original descriptions.

| Package | SHA-256 over sorted relative paths and file digests |
| --- | --- |
| Original, corrected | `beaea17fb0277a7400b721d60267ae44c773e534c1d547dedb282aa3c12d56df` |
| Candidate descriptions | `45b586a467deb25d1f69010486c5531fb85feadc3137ff22b39c2f66ec9ddd87` |
| Guide split | `08cc3909bb978977a91f293f5ba90a0b209c2941bdb20d621968c229d723e6ad` |

For selective installation, each command below creates a fresh project and home, uses the pinned public installer, and checks both files on disk and the native harness inventory.

```sh
python3 internal/discovery-evals/selective.py --out /tmp/scandit-subset --agent codex
python3 internal/discovery-evals/selective.py --out /tmp/scandit-subset --agent claude-code
```

Both installs exposed exactly one Scandit skill, `barcode-capture-rn`. The project copies lived under `.agents/skills/` for Codex and `.claude/skills/` for Claude Code. The installer lock recorded the same content hash, `b665ac84db01d27c9f50079966c95e9022e291854468b9a4381348d23358a006`. The public distribution inspected by the installer exposed 86 skills at the time, before the Linux correction. The subset check measures inventory only. Hosted marketplace model sessions and other harnesses were outside this pilot.
