"""Deterministic JD-vs-CV gap report. The host LLM does the rewriting; this keeps it honest."""
from __future__ import annotations

import re

from .schema import flatten_text

# canonical term -> surface forms to look for (lowercase). Extend freely.
VOCAB: dict[str, list[str]] = {
    "LLMs": ["llm", "llms", "large language model", "large language models"],
    "RAG": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "Microsoft Azure": ["azure", "microsoft azure", "azure ai foundry", "azure openai"],
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud", "vertex ai"],
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "Hugging Face": ["hugging face", "huggingface", "transformers"],
    "LangChain": ["langchain"],
    "LangGraph": ["langgraph"],
    "LangSmith": ["langsmith"],
    "OpenAI API": ["openai"],
    "Vector databases": ["pinecone", "vector database", "vector db", "faiss", "chroma", "weaviate"],
    "Prompt engineering": ["prompt engineering", "prompt design"],
    "Python": ["python"],
    "FastAPI": ["fastapi"],
    "Docker": ["docker", "containeri"],
    "Kubernetes": ["kubernetes", "k8s"],
    "MLOps": ["mlops", "model deployment", "model monitoring"],
    "Big data": ["big data", "spark", "databricks", "hadoop", "large datasets"],
    "SQL": ["sql"],
    "NLP": ["nlp", "natural language processing"],
    "Fine-tuning": ["fine-tuning", "fine tuning", "finetuning", "lora"],
    "Agents": ["agent", "agents", "agentic", "multi-agent"],
    "Machine learning": ["machine learning", "ml"],
    "Deep learning": ["deep learning", "neural network"],
    "CI/CD": ["ci/cd", "cicd", "github actions"],
    "Observability": ["observability", "tracing", "monitoring"],
}

# Terms that are often typos or legacy meanings; the server flags them so the user can confirm.
AMBIGUOUS: dict[str, str] = {
    "aiml": "Probably a typo for 'AI/ML'. Literal AIML is the legacy XML chatbot markup language (AliceBot); "
    "confirm with the user before treating it as a skill.",
    "ai/ml": "Read as 'AI and machine learning'.",
}


def _has(text: str, forms: list[str]) -> bool:
    for f in forms:
        # word-ish boundary; 'containeri' style stems match as prefixes
        pat = r"(?<![a-z0-9])" + re.escape(f) + (r"" if f.endswith("i") and len(f) > 8 else r"(?![a-z0-9])")
        if re.search(pat, text):
            return True
    return False


def gap_report(cv: dict, job_description: str) -> dict:
    jd = job_description.lower()
    cv_text = flatten_text(cv).lower()

    required = [term for term, forms in VOCAB.items() if _has(jd, forms)]
    matched = [t for t in required if _has(cv_text, VOCAB[t])]
    gaps = [t for t in required if t not in matched]

    ambiguous = {
        term: note for term, note in AMBIGUOUS.items() if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", jd)
    }
    years = re.findall(r"(\d+)\s*[-–to]+\s*(\d+)\s*years", jd)

    return {
        "jd_terms_found": required,
        "already_in_cv": matched,
        "gaps": gaps,
        "coverage_pct": round(100 * len(matched) / len(required)) if required else None,
        "ambiguous_terms": ambiguous,
        "experience_range_years": years[0] if years else None,
        "instructions": (
            "For each item in `gaps`, ask the user whether they have genuine experience. "
            "Add it only if they confirm, using their wording. Never invent experience, tools or numbers. "
            "Resolve `ambiguous_terms` with the user before using them."
        ),
    }
