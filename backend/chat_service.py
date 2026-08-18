import os

import numpy as np
import pandas as pd

try:
    from groq import Groq
    GROQ_SDK_AVAILABLE = True
except ImportError:
    GROQ_SDK_AVAILABLE = False

MODEL_NAME = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
FALLBACK_MODEL = "openai/gpt-oss-20b"

SUGGESTED_QUESTIONS = [
    "What are the main trends in this dataset?",
    "Which columns have the strongest correlation?",
    "What are the key statistics for the numeric columns?",
    "Are there any anomalies or outliers I should know about?",
    "What data quality issues exist?",
    "Summarize the distribution of values across categories",
    "Which column has the most missing data and why might that be?",
    "Give me a business interpretation of this dataset",
    "What further analysis would you recommend?",
    "Write pandas code to find the top 5 rows by the highest numeric value",
]

QUICK_ACTIONS = {
    "auto_insights": "Analyze this dataset and provide 5-7 key insights about patterns, trends, data quality, and business implications. Be specific and mention actual column names and values.",
    "stats_summary": "Give me a detailed statistical summary with key observations about distributions, central tendency, spread, and any notable patterns for each numeric column.",
    "quality_report": "Analyze data quality issues: missing values, duplicates, outliers, inconsistencies, and format problems. Provide specific recommendations to fix each issue.",
    "suggestions": "Based on the dataset structure, suggest 5 specific analytical approaches, visualizations, or ML models that would be valuable to apply. Explain why each is appropriate.",
    "generate_code": "Write useful pandas code snippets (5-6 examples) for exploring and analyzing this dataset. Include data filtering, aggregation, and visualization code. Use the actual column names.",
}

_client = None


def _get_client():
    """Lazily build a Groq client from the GROQ_API_KEY env var."""
    global _client
    if not GROQ_SDK_AVAILABLE:
        return None
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    if _client is None:
        _client = Groq(api_key=api_key)
    return _client


def status() -> dict:
    if not GROQ_SDK_AVAILABLE:
        return {
            "available": False,
            "model": None,
            "message": "`groq` package not installed. Run `pip install groq` and restart.",
        }
    if not os.environ.get("GROQ_API_KEY"):
        return {
            "available": False,
            "model": None,
            "message": (
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys and set it as an environment "
                "variable (see .env.example)."
            ),
        }
    try:
        client = _get_client()
        
        client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return {
            "available": True,
            "model": MODEL_NAME,
            "message": f"Connected to Groq Cloud — using model: {MODEL_NAME}",
        }
    except Exception as e:
        return {"available": False, "model": None, "message": f"Can't reach Groq: {e}"}


def _build_system_prompt(df: pd.DataFrame) -> str:
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    col_info = []
    for col in df.columns:
        s = df[col]
        info = f"  - {col} ({s.dtype}): {s.nunique()} unique, {s.isnull().sum()} missing"
        if pd.api.types.is_numeric_dtype(s):
            info += f", min={round(s.min(), 2)}, max={round(s.max(), 2)}, mean={round(s.mean(), 2)}"
        else:
            top = s.value_counts().head(3).index.tolist()
            info += f", top values: {top}"
        col_info.append(info)

    return f"""You are a data analyst assistant with expert knowledge of statistics and data science.

You are analyzing a dataset with the following structure:
- Shape: {df.shape[0]} rows x {df.shape[1]} columns
- Numeric columns: {num_cols}
- Categorical columns: {cat_cols}
- Missing cells: {df.isnull().sum().sum()} ({round(df.isnull().mean().mean() * 100, 1)}%)

Column details:
{chr(10).join(col_info)}

Sample data (5 rows):
{df.sample(min(5, len(df))).to_csv(index=False)}

Instructions:
- Answer questions about this dataset clearly and concisely
- Provide statistical insights when relevant
- Suggest actionable next steps when appropriate
- Format numbers nicely (use commas, round appropriately)
- If asked for code, provide clean Python/pandas code
- Be direct and specific — avoid generic filler text
"""


def ask_groq(messages: list, df: pd.DataFrame) -> str:
    if not GROQ_SDK_AVAILABLE:
        return "\u26a0\ufe0f `groq` package not installed. Run: `pip install groq`"

    client = _get_client()
    if client is None:
        return (
            "\u26a0\ufe0f GROQ_API_KEY is not set. Get a free key at "
            "https://console.groq.com/keys and set it as an environment variable."
        )

    system_prompt = _build_system_prompt(df)
    trimmed = messages[-20:]  

    def _call(model):
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, *trimmed],
            temperature=0.3,
            max_tokens=1024,
        )

    try:
        try:
            response = _call(MODEL_NAME)
        except Exception as e:
            
            if "model" in str(e).lower():
                response = _call(FALLBACK_MODEL)
            else:
                raise
        return response.choices[0].message.content
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid api key" in err.lower():
            return "\u26a0\ufe0f Invalid GROQ_API_KEY. Check your key at https://console.groq.com/keys"
        if "429" in err or "rate limit" in err.lower():
            return "\u26a0\ufe0f Groq rate limit reached. Wait a moment and try again."
        return f"\u26a0\ufe0f Groq error: {err}"



ask_ollama = ask_groq


def quick_insights(df: pd.DataFrame) -> str:
    insights = []
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    miss = df.isnull().mean() * 100
    high_miss = miss[miss > 20]
    if len(high_miss) > 0:
        insights.append(f"High missing data: {', '.join(f'{c} ({v:.1f}%)' for c, v in high_miss.items())}")
    else:
        insights.append("Missing data: Low — dataset is mostly complete.")

    dups = df.duplicated().sum()
    if dups > 0:
        insights.append(f"Duplicates: {dups} duplicate rows found ({round(dups / len(df) * 100, 1)}%)")

    for col in num_cols[:5]:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        skew = s.skew()
        if abs(skew) > 1:
            direction = "right" if skew > 0 else "left"
            insights.append(f"{col}: Skewed {direction} (skewness = {skew:.2f})")

        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outliers = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()
        if outliers > 0:
            insights.append(f"{col}: {outliers} potential outliers detected")

    for col in cat_cols[:5]:
        u = df[col].nunique()
        if u == len(df):
            insights.append(f"{col}: Looks like a unique ID column ({u} unique values)")
        elif u == 1:
            insights.append(f"{col}: Constant column — only 1 unique value")
        elif u < 5:
            insights.append(f"{col}: Low cardinality — {u} categories: {df[col].unique().tolist()}")

    return "\n\n".join(insights) if insights else "Dataset looks clean with no major issues detected."