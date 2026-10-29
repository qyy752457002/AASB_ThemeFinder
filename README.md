# AASB ThemeFinder

AASB ThemeFinder is a fork of [i-dot-ai/themefinder](https://github.com/i-dot-ai/themefinder), adapted to analyse organisational submissions to the **Australian Accounting Standards Board (AASB) Exposure Draft ED SR1 — *Australian Sustainability Reporting Standards: Disclosure of Climate-related Financial Information***.

It keeps the upstream architecture (a LangChain-based, multi-stage LLM pipeline over a `response_id` / `response` DataFrame), but rewrites the prompts and adjusts the data models so the outputs fit a standard-setting context: question-type-aware position classification, stance-neutral policy themes, and an evidence filter for submissions that regulators could actually cite.

> [!IMPORTANT]
> This is a research tool developed as part of an RMIT PhD project. Outputs are intended to support, not replace, professional judgement by analysts and standard-setters. The prompts are written specifically for ED SR1 (Q1–Q35); using them for another consultation requires editing the prompts (see [Adapting to another consultation](#adapting-to-another-consultation)).


## What is different from upstream ThemeFinder

### Prompts (`src/themefinder/prompts/`)

| Prompt | Upstream behaviour | AASB version |
|---|---|---|
| `consultation_system_prompt.txt` | Generic consultation-analysis system prompt | Frames the model as an analysis system for ED SR1. Sets principles (neutrality, faithfulness to submissions, auditability, policy relevance), the Australian jurisdictional context (ASRS, IFRS S1/S2, NFP and public sector reporting, NGER) and explicit limits (no policy drafting, no recommendations on behalf of the AASB). |
| `sentiment_analysis.txt` | `AGREEMENT` / `DISAGREEMENT` / `UNCLEAR` for every question | Classifies each response by **ED SR1 question type** (see [Question types](#ed-sr1-question-types-and-position-values)), with worked examples drawn from real submissions (HoTARAC, EY, CA ANZ, PRI). |
| `theme_generation.txt` | Themes carry a `position` | Exploratory extraction of substantive points, concerns, rationales and recommendations. Position is **not** assigned here (it is already handled by sentiment analysis). Empty or non-substantive responses produce no themes. |
| `theme_condensation.txt` | Merge similar themes | Merges by policy equivalence ("would a policymaker respond with the same drafting action?"). Themes about different sections of the standard, different entity types, or needing different policy responses are kept apart. `source_topic_count` is tracked as signal strength. |
| `theme_refinement.txt` | Standardise wording | Produces the final theme set as `"Label: Description"` (exactly one colon). Themes are stance-neutral (no "support"/"oppose") and use AASB / IFRS S1–S2 / ASRS / NGER terminology. |
| `theme_target_alignment.txt` | Reduce to *N* themes | Rolls refined themes up into at most *N* high-level **policy categories** for consultation summaries and briefings, preserving regulatory context and cumulative `source_topic_count`. |
| `theme_mapping.txt` | Map responses to themes | Pure thematic classification (sentiment is ignored). Prefers under-tagging to speculative tagging. Empty or procedural responses are labelled `["UNCLEAR"]`; the label list is never empty. |
| `detail_detection.txt` | Flag detailed responses | Flags a response as `EVIDENCE_RICH = YES` only if it addresses the question **and** gives concrete support: named legislation/standards/schemes, specific examples (e.g. NFPs, super funds, public sector entities), or contextualised organisational experience. Test: *could this be cited in a consultation summary or Board briefing?* |

The cross-cutting and agentic-clustering prompts (`cross_cutting_*.txt`, `agentic_theme_clustering.txt`) are unchanged from upstream.

### Code (`src/themefinder/`)

- **`models.py`**
  - `Position` is extended to cover all three ED SR1 question types: `AGREEMENT`, `DISAGREEMENT`, `OPTION_1`, `OPTION_2`, `OPTION_3`, `OPTION_OTHER`, `ANSWERED`, `NO_ADDITIONAL_GUIDANCE`, and `NO_RESPONSE` (the enum member is still named `UNCLEAR` for backwards compatibility, but its value is `"NO_RESPONSE"`).
  - `Theme` no longer has a `position` field, matching the stance-neutral generation prompt.
  - `ThemeGenerationResponses` accepts an empty list, so a batch with no substantive content is a valid "no themes" result rather than a validation failure that triggers retries.
- **`tasks.py`**
  - All stages call the LLM through `_structured_output()`, which requests structured output with `include_raw=False` (falls back for older `langchain_core`).
  - `theme_condensation` passes the current themes to the prompt as `topics`.
  - `theme_mapping` handles an empty theme set: every response is labelled `["UNCLEAR"]` instead of calling the LLM.
- **`llm_batch_processor.py`**
  - Prompt files are always read as UTF-8 (avoids `GBK` decode errors on Windows), and `load_prompt_from_file` accepts a bare name, a relative path or an absolute path.
  - `max_prompt_length` raised from 50,000 to 110,000 tokens, since ED SR1 submissions are long.
  - Token counting maps Azure deployment names (e.g. `gpt-4.1`, `gpt-35-turbo`) to tiktoken model names, and falls back to `cl100k_base` for unknown models.
  - Structured output is unwrapped from `AIMessage.parsed`, and the resulting Pydantic serializer warnings are silenced.


## ED SR1 question types and position values

The sentiment stage assigns exactly one `position` per response, using only the values allowed for that question's type:

| Question type | Questions | Allowed `position` values |
|---|---|---|
| Agree / disagree | Q2–Q5, Q7–Q11, Q13–Q20, Q22, Q23, Q25–Q27, Q29 | `AGREEMENT`, `DISAGREEMENT`, `NO_RESPONSE` |
| Multiple option | Q1 | `OPTION_1`, `OPTION_2`, `OPTION_3`, `OPTION_OTHER`, `NO_RESPONSE` |
| Open-ended descriptive | Q6, Q12, Q21, Q24, Q28, Q30–Q35 | `ANSWERED`, `NO_ADDITIONAL_GUIDANCE`, `NO_RESPONSE` |

The question-to-type mapping lives in both `prompts/sentiment_analysis.txt` and the `Position` docstring in `models.py`; keep them in sync if you change it.


## Pipeline

`find_themes()` runs the following stages for **one question** at a time:

1. **Sentiment analysis** — question-type-aware `position` per response (batch size 20).
2. **Theme generation** — exploratory, stance-neutral themes from batches of responses (batch size 50).
3. **Theme condensation** — merges overlapping themes, recursively if there are more themes than the batch size (batch size 75).
4. **Theme refinement** — final `"Label: Description"` themes with sequential `topic_id`s (A, B, C, …).
5. **Theme target alignment** *(optional)* — rolls themes up to at most `target_n_themes` policy categories. Runs only when `target_n_themes` is set.
6. **Theme mapping** — assigns each response one or more `topic_id`s, or `UNCLEAR`.
7. **Detail detection** — flags evidence-rich responses (`YES` / `NO`).

Every stage is also exported on its own (`sentiment_analysis`, `theme_generation`, `theme_condensation`, `theme_refinement`, `theme_target_alignment`, `theme_mapping`, `detail_detection`), each taking a custom `prompt_template` if you want to override the bundled prompt.


## Installation

Install this fork from source. **Do not** run `pip install themefinder`: that installs the upstream PyPI package, which does not contain the AASB prompts or model changes.

```bash
git clone https://github.com/qyy752457002/AASB_ThemeFinder.git
cd AASB_ThemeFinder
pip install -e .        # or: poetry install
```

If the upstream package is already installed, run `pip uninstall themefinder` first. To check that the local copy is the one being imported:

```python
import themefinder.tasks
print(themefinder.tasks.__file__)  # should point into this repository, not site-packages
```

See [INSTALL_LOCAL.md](INSTALL_LOCAL.md) for more detail. Requires Python 3.10–3.12.

### LLM configuration

Any LangChain chat model that supports structured output can be used. For Azure OpenAI, put the following in a `.env` file and load it with `python-dotenv`:

```
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
OPENAI_API_VERSION=
DEPLOYMENT_NAME=
MODEL_NAME=          # optional; used for token counting, defaults to gpt-4
```

For other providers, set whichever variables the corresponding LangChain integration requires.


## Input data

ThemeFinder takes a pandas DataFrame with two columns, for a single question:

- `response_id` — unique integer > 0
- `response` — the free-text response

In this project, submissions are stored as one JSON file per organisation, each holding a list of per-question responses:

```json
[
  {"question_id": "Q1", "organization": "Example Org", "response_text": "..."},
  {"question_id": "Q2", "organization": "Example Org", "response_text": "..."}
]
```

Question wording is held separately in `questions.json`:

```json
[
  {"question_id": "Q1", "content": "In respect of presenting the core content disclosure requirements of IFRS S1, do you prefer: ..."}
]
```


## Usage

The script below loads all responses, then runs the pipeline once per question and writes `result_<question_id>.json`.

```python
import asyncio
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from themefinder import find_themes

load_dotenv()

llm = AzureChatOpenAI(model_name="gpt-4o", temperature=0)


def load_questions(path: Path) -> dict[str, str]:
    questions = json.loads(path.read_text(encoding="utf-8"))
    return {q["question_id"]: q["content"] for q in questions}


def load_responses(responses_dir: Path) -> pd.DataFrame:
    records = []
    for file in sorted(responses_dir.glob("*.json")):
        records.extend(json.loads(file.read_text(encoding="utf-8")))
    df = pd.DataFrame(records).rename(columns={"response_text": "response"})
    df["response_id"] = df.index + 1
    return df


async def process_question(question_id: str, question_text: str, df: pd.DataFrame):
    result = await find_themes(
        df[["response_id", "response"]],
        llm,
        question_text,
        target_n_themes=None,  # e.g. 8 to enable target alignment
        concurrency=10,
    )
    output = {
        "question_id": question_id,
        "question_text": question_text,
        "organizations": df[["response_id", "organization"]].to_dict(orient="records"),
        **{
            key: result[key].to_dict(orient="records")
            for key in ["sentiment", "themes", "mapping", "detailed_responses", "unprocessables"]
        },
    }
    Path(f"result_{question_id}.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def main():
    questions = load_questions(Path("questions.json"))
    responses = load_responses(Path("Responses"))

    for qid in sorted(responses["question_id"].unique()):
        if qid not in questions:
            print(f"Skipping {qid}: not found in questions.json")
            continue
        await process_question(qid, questions[qid], responses[responses["question_id"] == qid])


if __name__ == "__main__":
    asyncio.run(main())
```

> [!NOTE]
> `find_themes` uses the AASB system prompt (`consultation_system_prompt.txt`) by default. Passing your own `system_prompt=` **replaces** it rather than adding to it, so only do so if you intend to supply the full context yourself.

A worked example that runs Q1 for the first 10 organisations is in [examples/process_first_10_responses.py](examples/process_first_10_responses.py).

### Output

`find_themes` returns a dictionary:

| Key | Content |
|---|---|
| `question` | The question text |
| `sentiment` | `response_id`, `position` |
| `themes` | `topic_id`, `topic` (`"Label: Description"`), `source_topic_count` |
| `mapping` | `response_id`, `labels` (list of `topic_id`s, or `["UNCLEAR"]`) |
| `detailed_responses` | `response_id`, `evidence_rich` (`YES` / `NO`) |
| `unprocessables` | Responses the LLM could not process in the sentiment or mapping stages |

The response-level DataFrames (`sentiment`, `mapping`, `detailed_responses`) also keep the original `response` column.

`source_topic_count` counts how many generated themes were merged into a final theme. It indicates how prominent an issue is across theme batches, **not** how many respondents raised it; use `mapping` to count respondents.


## Adapting to another consultation

The prompts hard-code ED SR1 context. To reuse the pipeline for a different exposure draft:

1. Rewrite `consultation_system_prompt.txt` for the new consultation and jurisdiction.
2. Update the question-type lists and examples in `sentiment_analysis.txt`, and the `Position` enum in `models.py` if new position values are needed.
3. Replace the "AASB ED SR1 Consultation" references and illustrative examples in the other stage prompts.

Alternatively, pass a custom `prompt_template` to individual stage functions without editing the package.


## Development

```bash
pytest
```

The upstream evaluation scripts (`evals/`) and docs (`docs/`, `mkdocs.yml`) are retained but have not been updated for the AASB prompts.


## Acknowledgements and licence

Based on [ThemeFinder](https://github.com/i-dot-ai/themefinder) by the UK Government's Incubator for AI (i.AI). Upstream documentation: <https://i-dot-ai.github.io/themefinder/>.

Licensed under the MIT License — see [LICENCE](LICENCE). The upstream documentation is © Crown copyright and available under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

Please direct questions about this fork to the repository owner, not to the upstream maintainers.
