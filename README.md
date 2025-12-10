# ThemeFinder

ThemeFinder is a topic modelling Python package designed for analysing one-to-many question-answer data (i.e. survey responses, public consultations, etc.). See the [docs](https://i-dot-ai.github.io/themefinder/) for more info.

> [!IMPORTANT]
> Incubation project: This project is an incubation project; as such, we don't recommend using this for critical use cases yet. We are currently in a research stage, trialling the tool for case studies across the Civil Service. Find out more about our projects at https://ai.gov.uk/. 


## Quickstart

### Install using your package manager of choice

For example `pip install themefinder` or `poetry add themefinder`.

### Usage

ThemeFinder takes as input a [pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) with two columns:
- `response_id`: A unique identifier for each response
- `response`: The free text survey response

ThemeFinder now supports a range of language models through structured outputs.

The function `find_themes` identifies common themes in responses and labels them, it also outputs results from intermediate steps in the theme finding pipeline.

For this example, import the following Python packages into your virtual environment: `asyncio`, `pandas`, `lanchain`. And import `themefinder` as described above.

If you are using environment variables (eg for API keys), you can use `python-dotenv` to read variables from a `.env` file. 

If you are using an Azure OpenAI endpoint, you will need the following variables:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `OPENAI_API_VERSION`
- `DEPLOYMENT_NAME`
- `AZURE_OPENAI_BASE_URL`

Otherwise you will need whichever variables [LangChain](https://www.langchain.com/) requires for your LLM of choice.

```python
import asyncio
import json
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from themefinder import find_themes

# Load .env
load_dotenv()

# ==========================
# Load questions.json
# ==========================
def load_questions():
    with Path("questions.json").open("r", encoding="utf-8") as f:
        questions_raw = json.load(f)

    # Convert to dictionary: {"Q1": "full question text", ...}
    questions_dict = {q["question_id"]: q["content"] for q in questions_raw}
    return questions_dict

# ==========================
# Load responses.json
# ==========================
def load_responses():
    with Path("responses.json").open("r", encoding="utf-8") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw)
    df["response_id"] = df.index + 1
    df = df.rename(columns={"response_text": "response"})
    return df

# ==========================
# Initialise LLM
# ==========================
# Note: "gpt-5" may not exist. Common models: "gpt-4o", "gpt-4-turbo", "gpt-4"
# If you encounter errors, try changing to a valid model name
llm = ChatOpenAI(
    model="gpt-4o",  # TODO: Verify this model exists. If not, use "gpt-4o" or "gpt-4-turbo"
    temperature=0,
)

# ==========================
# System Prompt
# ==========================
system_prompt = (
    "You are analysing consultation responses to AASB ED SR1. "
    "When generating themes, ALWAYS output 'Label: Description'. "
    "If the submission includes multiple viewpoints, identify the dominant overall position."
)

# ==========================
# Main: Loop through questions
# ==========================
async def process_single_question(question_id, question_text, df):

    print(f"\n==============================")
    print(f"➡ Processing {question_id}")
    print(f"==============================")

    # Clean dataframe for themefinder
    theme_df = df[["response_id", "response"]]

    # Run theme extraction
    result = await find_themes(
        theme_df,
        llm,
        question_text,
        system_prompt=system_prompt
    )

    # Build JSON output
    output = {
        "question_id": question_id,
        "question_text": question_text,
        "sentiment": result["sentiment"].to_dict(orient="records"),
        "themes": result["themes"].to_dict(orient="records"),
        "mapping": result["mapping"].to_dict(orient="records"),
        "detailed_responses": result["detailed_responses"].to_dict(orient="records"),
        "unprocessables": result["unprocessables"].to_dict(orient="records")
    }

    # Save file (e.g. result_Q1.json)
    out_path = Path(f"result_{question_id}.json")
    out_path.write_text(json.dumps(output, indent=4, ensure_ascii=False), encoding="utf-8")

    print(f"✔ Saved result for {question_id}: {out_path.resolve()}")


async def main():

    # Load both files
    responses_df = load_responses()
    questions_dict = load_questions()

    print("\n=== Loaded responses.json ===")
    print(responses_df)

    # Get all question_ids that appear in responses.json
    unique_question_ids = sorted(responses_df["question_id"].unique())

    print("\n=== Detected question_ids ===")
    print(unique_question_ids)

    # Process each question in a loop
    for qid in unique_question_ids:

        if qid not in questions_dict:
            print(f"❌ WARNING: Cannot find {qid} in questions.json, skipping.")
            continue

        # Filter responses for this question
        df_subset = responses_df[responses_df["question_id"] == qid].copy()

        question_text = questions_dict[qid]

        # Call processing function
        await process_single_question(qid, question_text, df_subset)

        time.sleep(1)

    print("\n🎉 All questions processed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
```

## ThemeFinder pipeline

ThemeFinder's pipeline consists of five distinct stages, each utilizing a specialized LLM prompt:

### Sentiment analysis
- Analyses the emotional tone and position of each response using sentiment-focused prompts
- Provides structured sentiment categorisation based on LLM analysis

### Theme generation
- Uses exploratory prompts to identify initial themes from response batches
- Groups related responses for better context through guided theme extraction

### Theme condensation
- Employs comparative prompts to combine similar or overlapping themes
- Reduces redundancy in identified topics through systematic theme evaluation

### Theme refinement
- Leverages standardisation prompts to normalise theme descriptions
- Creates clear, consistent theme definitions through structured refinement

### Theme target alignment
- Optional step to consolidate themes down to a target number

### Theme mapping
- Utilizes classification prompts to map individual responses to refined themes
- Supports multiple theme assignments per response through detailed analysis


The prompts used at each stage can be found in `src/themefinder/prompts/`.

The file `src/themefinder.core.py` contains the function `find_themes` which runs the pipline. It also contains functions fo each individual stage.


**For more detail - see the docs: [https://i-dot-ai.github.io/themefinder/](https://i-dot-ai.github.io/themefinder/).**


## Model Compatibility

ThemeFinder's structured output approach makes it compatible with a wide range of language models from various providers. This list is non-exhaustive, and other models may also work effectively:

### OpenAI Models
- GPT-4, GPT-4o, GPT-4.1
- All Azure OpenAI deployments

### Google Models
- Gemini series (1.5 Pro, 2.0 Pro, etc.)

### Anthropic Models
- Claude series (Claude 3 Opus, Sonnet, Haiku, etc.)

### Open Source Models
- Llama 2, Llama 3
- Mistral models (e.g., Mistral 7B, Mixtral)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The documentation is [© Crown copyright](https://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/uk-government-licensing-framework/crown-copyright/) and available under the terms of the [Open Government 3.0 licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).


## Feedback

Contact us with questions or feedback at packages@cabinetoffice.gov.uk.
