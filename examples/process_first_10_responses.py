"""
Example: Processing First 10 Response Files through ThemeFinder Pipeline

This script demonstrates how ThemeFinder processes responses from the first 10 organizations
in the Responses folder through the complete pipeline.

Organizations:
1. ABS_edsr1_abs
2. Zenith Investment Partners_edsr1_zenith
3. Yarra Capital Management (YCM)_edsr1_ycm
4. Whitehaven Coal_edsr1_whitehavencoal
5. Westpac Group_edsr1_westpac
6. Waverly Council NSW_edsr1_waverlynsw
7. Water Services Association of Australia (WSAA)_edsr1_wsaa
8. Victoria University and Michael Jensen & Associates_edsr1_vicunimichaeljensenassociates
9. UNSW_edsr1_unsw
10. University Pension Plan (UPP)_edsr1_upp
"""

import asyncio
import json
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from themefinder import find_themes

# Load environment variables
load_dotenv()

# First 10 organizations to process
FIRST_10_ORGS = [
    "ABS_edsr1_abs",
    "Zenith Investment Partners_edsr1_zenith",
    "Yarra Capital Management (YCM)_edsr1_ycm",
    "Whitehaven Coal_edsr1_whitehavencoal",
    "Westpac Group_edsr1_westpac",
    "Waverly Council NSW_edsr1_waverlynsw",
    "Water Services Association of Australia (WSAA)_edsr1_wsaa",
    "Victoria University and Michael Jensen & Associates_edsr1_vicunimichaeljensenassociates",
    "UNSW_edsr1_unsw",
    "University Pension Plan (UPP)_edsr1_upp",
]


def load_responses_from_files(org_names: list[str], responses_dir: Path) -> pd.DataFrame:
    """
    Load responses from JSON files for specified organizations.
    
    Each JSON file contains an array of response objects with:
    - question_id: e.g., "Q1", "Q2"
    - organization: organization name
    - response_text: the actual response text
    
    Returns:
        DataFrame with columns: question_id, organization, response_text, response_id
    """
    all_responses = []
    
    for org_name in org_names:
        # Construct filename from organization name
        # Format: "Organization Name_edsr1_orgkey.json"
        filename = f"{org_name}.json"
        file_path = responses_dir / filename
        
        if not file_path.exists():
            print(f"⚠️  File not found: {filename}")
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            org_responses = json.load(f)
            
        # Add each response to the list
        for resp in org_responses:
            all_responses.append({
                "question_id": resp["question_id"],
                "organization": resp["organization"],
                "response_text": resp["response_text"]
            })
    
    # Convert to DataFrame
    df = pd.DataFrame(all_responses)
    
    # Add response_id (sequential ID across all responses)
    df["response_id"] = df.index + 1
    
    # Rename response_text to response for ThemeFinder compatibility
    df = df.rename(columns={"response_text": "response"})
    
    print(f"✅ Loaded {len(df)} responses from {len(org_names)} organizations")
    print(f"   Questions covered: {sorted(df['question_id'].unique())}")
    
    return df


async def process_question_example(question_id: str, question_text: str, responses_df: pd.DataFrame):
    """
    Process a single question through the ThemeFinder pipeline.
    
    This demonstrates the complete 6-stage pipeline:
    1. Sentiment Analysis
    2. Theme Generation
    3. Theme Condensation
    4. Theme Refinement
    5. Theme Target Alignment (optional)
    6. Theme Mapping
    """
    print(f"\n{'='*60}")
    print(f"Processing {question_id}")
    print(f"{'='*60}")
    print(f"Question: {question_text[:100]}...")
    print(f"Number of responses: {len(responses_df)}")
    
    # Filter responses for this question
    question_responses = responses_df[responses_df["question_id"] == question_id].copy()
    
    if len(question_responses) == 0:
        print(f"⚠️  No responses found for {question_id}")
        return None
    
    # Initialize LLM
    llm = AzureChatOpenAI(
        model_name="gpt-4o",
        temperature=0,
    )
    
    # Prepare DataFrame for ThemeFinder (needs response_id and response columns)
    theme_df = question_responses[["response_id", "response"]].copy()
    
    print(f"\n📊 Pipeline Stages:")
    print(f"   1️⃣  Sentiment Analysis: Analyzing {len(theme_df)} responses...")
    print(f"   2️⃣  Theme Generation: Extracting initial themes from batches...")
    print(f"   3️⃣  Theme Condensation: Combining similar themes...")
    print(f"   4️⃣  Theme Refinement: Standardizing theme descriptions...")
    print(f"   5️⃣  Theme Mapping: Mapping responses to final themes...")
    
    # Run the complete ThemeFinder pipeline
    result = await find_themes(
        theme_df,
        llm,
        question_text,
        target_n_themes=None,  # Optional: set to 10 to enable target alignment
        verbose=True,
        concurrency=10,
    )
    
    # Display results summary
    print(f"\n📈 Results Summary:")
    print(f"   • Sentiment classifications: {len(result['sentiment'])}")
    print(f"   • Final themes identified: {len(result['themes'])}")
    print(f"   • Response-to-theme mappings: {len(result['mapping'])}")
    print(f"   • Unprocessable responses: {len(result['unprocessables'])}")
    
    # Show sample themes
    if len(result['themes']) > 0:
        print(f"\n🎯 Sample Themes (first 3):")
        for idx, theme in result['themes'].head(3).iterrows():
            topic = theme.get('topic', f"{theme.get('topic_label', 'N/A')}: {theme.get('topic_description', 'N/A')}")
            print(f"   {idx + 1}. {topic}")
    
    return result


async def main():
    """
    Main function demonstrating the complete processing workflow.
    """
    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    responses_dir = project_root / "Responses"
    
    print("="*60)
    print("ThemeFinder Pipeline Processing Example")
    print("Using First 10 Organizations")
    print("="*60)
    
    # Step 1: Load responses from JSON files
    print("\n📂 Step 1: Loading Response Files")
    print("-" * 60)
    responses_df = load_responses_from_files(FIRST_10_ORGS, responses_dir)
    
    # Step 2: Process a sample question (Q1 as example)
    print("\n🔍 Step 2: Processing Question Q1")
    print("-" * 60)
    
    # Example question text (you would load this from questions.json in practice)
    sample_question = (
        "In respect of presenting the core content disclosure requirements of IFRS S1, "
        "do you prefer: (a) Option 1 – one ASRS Standard that would combine the relevant "
        "contents of IFRS S1 relating to general requirements and judgements, uncertainties "
        "and errors (i.e. all relevant requirements other than those relating to the core "
        "content that are exactly the same as the requirements in IFRS S2) within an "
        "Australian equivalent of IFRS S2; (b) Option 2 – two ASRS Standards where the "
        "same requirements in respect to disclosures of governance, strategy and risk "
        "management would be included in both Standards; (c) Option 3 – two ASRS Standards, "
        "by including in [draft] ASRS 1 the requirements relating to disclosures of governance, "
        "strategy and risk management, and in [draft] ASRS 2, replacing duplicated content "
        "with Australian-specific paragraphs cross-referencing to the corresponding paragraphs "
        "in [draft] ASRS 1 (which is the option adopted by the AASB in developing the "
        "[draft] ASRS 1 and [draft] ASRS 2 in this Exposure Draft); (d) another presentation "
        "approach (please provide details of that presentation method)? Please provide reasons "
        "to support your view."
    )
    
    result = await process_question_example("Q1", sample_question, responses_df)
    
    if result:
        # Save results to file
        output_file = project_root / "Tools" / "AASB_ThemeFinder" / "examples" / "result_Q1_example.json"
        output_data = {
            "question_id": "Q1",
            "question_text": sample_question,
            "organizations_processed": FIRST_10_ORGS,
            "sentiment": result["sentiment"].to_dict(orient="records"),
            "themes": result["themes"].to_dict(orient="records"),
            "mapping": result["mapping"].to_dict(orient="records"),
            "detailed_responses": result["detailed_responses"].to_dict(orient="records"),
            "unprocessables": result["unprocessables"].to_dict(orient="records")
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
    
    print("\n✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
