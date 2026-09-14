# JEE Dataset Audit

_Written 2026-09-14. Every entry below was checked against the dataset's
own repo/card/paper this session (not memory). Feeds
[`research-validation-report.md`](research-validation-report.md) Q6–Q8._

## Summary table

| Source | URL | License (as stated on the source) | Questions | Subjects / Years | Answers | Solutions | Topic/Subtopic | Difficulty | Real student interaction data | Usable for training a KT model? |
|---|---|---|---|---|---|---|---|---|---|---|
| JEEBench | github.com/dair-iitd/jeebench | MIT (confirmed in `LICENSE` file) | 515 (confirmed by parsing `data/dataset.json`) | Phy/Chem/Math; JEE Advanced 2016–2023 | Yes (`gold` field) | No | No | No | **No** | Question bank only — no topic/difficulty/student data |
| eQOURSE JEE Main Questions | huggingface.co/datasets/eQOURSE/jee-main-questions | "cc-by-4.0" (as stated on card) | ~2,307 (Chem 738 + Math 801 + Phy 768) | Phy/Chem/Math; years not summarized on card | Yes (`correct_option`) | Yes (`solution` field) | Yes (`topic`, `subtopic`) | Yes (`difficulty`: Easy/Moderate/Tough) | **No** | **Best-structured question bank — reuse as the item environment** |
| NalandaJEENEETBench | huggingface.co/datasets/Nalandadata/NalandaJEENEETBench | "CC BY-NC 4.0" (gated, no-redistribution clause) | 785 public benchmark sample + 500 `train_sample` w/ solutions; 116,000+ claimed but not publicly accessible | Phy/Chem/Math/Bio/Eng (JEE+NEET pool); years not stated | Yes (benchmark split) | Partial (`train_sample` only) | No | No | **No** | Smallest, most restricted, unverifiable large-set claim — skip |
| (broader search) | — | — | — | — | — | — | — | — | **None found anywhere** | No public JEE/NEET student-interaction dataset exists |

## Detail

### JEEBench
- Repo: github.com/dair-iitd/jeebench · Paper: aclanthology.org/2023.emnlp-main.468/
- Fields per item: `description`, `index`, `subject`, `type` (MCQ/MSQ/Integer/Numeric), `question`, `gold`.
- The `responses/` directories contain LLM-generated (GPT-3/3.5/4) chain-of-thought outputs used for benchmarking those models — these are model outputs, not authoritative human solutions or student data.
- Clean and small; useful as a correctness-grading environment for a simulated agent, but contributes nothing to concept/difficulty metadata or student behavior.

### eQOURSE JEE Main Questions
- huggingface.co/datasets/eQOURSE/jee-main-questions
- Fields: `question_type` (numerical/single_correct/multiple_choice), `subject`, `topic`, `subtopic`, `difficulty`, `correct_option`, `solution`, `has_image`.
- This is the only candidate with both concept-level metadata and difficulty — the two things a synthetic learner needs to condition its P(correct) on. **Recommended as the primary item environment for Phase 1.**
- License needs one more pass before any redistribution/derivative publishing (e.g. if the synthetic dataset is later published alongside question text) — confirm CC-BY-4.0 holds up under closer legal review; using it internally to build a simulator is not blocked by this.

### NalandaJEENEETBench
- huggingface.co/datasets/Nalandadata/NalandaJEENEETBench
- Access requires accepting HF dataset terms (no-redistribution clause) before download.
- The marketed "116,000+ expert-curated JEE and NEET questions" figure is **not accessible** — only the 785-question benchmark split and 500-question `train_sample` split are downloadable. Treat the larger number as an unverified marketing claim, not an available asset.
- Non-commercial license makes this the least flexible of the three even where it has usable content.

### Broader search: any real JEE/NEET student-interaction dataset?
**None found.** Checked `Reja1/jee-neet-benchmark` (question-only, same pattern as the others) and searched for Indian ed-tech platforms known to do JEE/NEET-scale KT internally — Embibe explicitly markets a "Deep Knowledge Tracing"-based "Concept Mastery" feature, and Unacademy/Toppr/Physics Wallah plausibly hold comparable data — but none publish it, and no academic paper surfaced using a released Indian-platform log for JEE/NEET-specific KT research.

The datasets that do have real longitudinal per-student KT-suitable data —
ASSISTments (2009/2012/2015), EdNet (Korean English-tutoring platform),
XES3G5M (Chinese K-12 math), Junyi Academy, DBE-KT22 — are real and public,
but none are JEE/NEET or India-curriculum content. Useful only as
**methodological templates** (data format, model architecture, splitting
protocol — see `experimental-protocol.md`), never as substitute JEE content.

## Practical implication

There is no dataset-discovery shortcut. The two ways forward are:
1. **Build the synthetic generator over eQOURSE's item pool** (this
   project's actual plan) — the only path that doesn't require a business
   partnership.
2. Pursue a data-sharing arrangement with an Indian ed-tech platform — a
   business/partnership problem, explicitly out of scope for this
   validation-and-spec phase.
