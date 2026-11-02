"""CV-Updater MCP server.

Flow the host LLM follows (see the `tailor_cv` prompt):
  import_cv -> (LLM structures) -> save_cv_data
  analyze_job -> (LLM + user resolve gaps) -> collect_preferences / set_preferences
  preview_templates -> user picks -> render_cv  (verification, page-fit and ATS check run inside)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from mcp.server.mcpserver import Elicit, ElicitationResult, Image, MCPServer, Resolve
from pydantic import BaseModel, Field

from . import analysis, config, extract, fit, schema, templates, verify
from .render import build_docx

mcp = MCPServer("CV-Updater")

Fmt = Literal["docx", "pdf", "both"]


# ───────────────────────── helpers ─────────────────────────
def _parse_cv_json(raw: str, what: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise schema.CVError(f"{what} is not valid JSON ({e}). Return a single JSON object, no markdown fences.") from e
    if not isinstance(data, dict):
        raise schema.CVError(f"{what} must be a JSON object.")
    return data


def _prefs() -> dict:
    return {"output_format": "both", "max_pages": 2, "ats_safe": True, "sections_to_drop": "", "tone": "balanced",
            **(config.read_json(config.prefs_path(), {}) or {})}


def _drop_sections(cv: dict, csv: str) -> dict:
    drop = {s.strip().lower() for s in csv.split(",") if s.strip()}
    return {k: v for k, v in cv.items() if k.lower() not in drop}


# ───────────────────────── resources ─────────────────────────
@mcp.resource("cv://profile")
def cv_profile() -> str:
    """The saved base CV (canonical JSON)."""
    return json.dumps(schema.load_cv(), indent=2, ensure_ascii=False)


@mcp.resource("cv://templates")
def cv_templates() -> str:
    """Available design templates."""
    return json.dumps(templates.catalog(), indent=2)


# ───────────────────────── prompts ─────────────────────────
@mcp.prompt()
def parse_cv_to_json(cv_text: str) -> str:
    """Instructions for turning raw CV text into the canonical JSON, with no invention."""
    return f"""Convert the CV text below into ONE JSON object with exactly this shape:

{json.dumps(schema.EXAMPLE_SCHEMA, indent=2)}

Rules:
- Copy facts exactly: names, employers, roles, dates, numbers, metrics, credential IDs. Never invent or "improve" them.
- Omit a section or field if the CV has nothing for it. Do not guess.
- Keep each bullet as one string, in the original order.
- Dates as written (e.g. "Jun 2025", "Present").
- Output only the JSON, then call `save_cv_data` with it.

CV TEXT:
{cv_text}"""


@mcp.prompt()
def tailor_cv(job_description: str) -> str:
    """Full workflow and rules for tailoring the saved CV to a job description."""
    cv = schema.load_cv()
    report = analysis.gap_report(cv, job_description)
    return f"""You are tailoring a CV to a job description. Follow these steps in order.

1. GAPS FIRST. Gap report for this JD:
{json.dumps(report, indent=2)}
   Ask the user about each gap and each ambiguous term. Include a skill or claim ONLY if they confirm genuine experience.
2. PREFERENCES. Call `collect_preferences` (or ask in chat and call `set_preferences`).
3. TAILOR. Produce a JSON object using the same schema as the base CV (you may return only the keys you changed:
   title, summary, skills, experience, projects). Rules:
   - Never invent employers, roles, dates, numbers, tools or outcomes. Every number must already be in the base CV.
   - Keep company/role/start/end/institution/degree exactly as in the base CV.
   - Reword bullets to use the JD's vocabulary where it is truthful. Order bullets most relevant first.
   - Put the strongest JD-relevant skills first; drop irrelevant ones if space is tight.
   - Write bullets as: strong verb + what + how (tools) + measurable result, only where the base CV supports it.
4. PREVIEW. Call `preview_templates` with your tailored JSON, show the user the images, and let them choose.
5. RENDER. Call `render_cv` with the chosen template_id. If it returns status "blocked", fix the listed problems and retry.
   Summarise warnings, trimmed bullets and the ATS check to the user.

BASE CV:
{json.dumps(cv, indent=2, ensure_ascii=False)}

JOB DESCRIPTION:
{job_description}"""


# ───────────────────────── import / save ─────────────────────────
@mcp.tool()
def import_cv(file_path: str) -> dict:
    """Extract raw text from a CV file (.pdf or .docx). Next: structure it with the `parse_cv_to_json` prompt, then `save_cv_data`."""
    text = extract.extract_text(file_path)
    return {"characters": len(text), "text": text,
            "next_step": "Structure this text using the parse_cv_to_json prompt, then call save_cv_data."}


@mcp.tool()
def save_cv_data(cv_json: str) -> dict:
    """Validate and save the structured base CV. The previous version is backed up with a timestamp."""
    cv = _parse_cv_json(cv_json, "cv_json")
    backup = schema.save_cv(cv)
    return {"saved": str(config.cv_path()), "backup": backup or None,
            "sections": [k for k in cv if cv[k]]}


# ───────────────────────── analysis ─────────────────────────
@mcp.tool()
def analyze_job(job_description: str) -> dict:
    """Compare the saved CV with a job description: which JD terms are covered, which are gaps, which are ambiguous."""
    return analysis.gap_report(schema.load_cv(), job_description)


# ───────────────────────── preferences ─────────────────────────
class Prefs(BaseModel):
    output_format: Fmt = Field("both", description="Which file(s) do you want: docx, pdf or both?")
    max_pages: int = Field(2, ge=1, le=3, description="Maximum number of pages (1-3)")
    ats_safe: bool = Field(True, description="Keep it simple and ATS-friendly (no decorative elements)?")
    sections_to_drop: str = Field("", description="Comma-separated sections to leave out, e.g. achievements,certifications")
    tone: Literal["concise", "balanced", "detailed"] = Field("balanced", description="How detailed should bullets be?")


QUESTIONS = [
    "Output format: docx, pdf or both?",
    "Maximum pages: 1, 2 or 3?",
    "ATS-safe (simple, plain) or visually richer?",
    "Any sections to leave out (e.g. achievements, certifications)?",
    "Bullet style: concise, balanced or detailed?",
]


def _ask_prefs() -> Elicit[Prefs]:
    return Elicit("A few quick questions before I update your CV:", Prefs)


@mcp.tool()
def collect_preferences(answer: Annotated[ElicitationResult[Prefs], Resolve(_ask_prefs)]) -> dict:
    """Ask the user their CV preferences through an interactive form (MCP elicitation) and save them.
    If the client cannot show forms and this call errors, call `preference_questions`, ask in chat,
    then call `set_preferences`."""
    if answer.action != "accept":
        return {"status": answer.action, "current": _prefs(), "note": "No changes saved; current preferences will be used."}
    prefs = answer.data.model_dump()
    config.write_json(config.prefs_path(), prefs)
    return {"status": "saved", "preferences": prefs}


@mcp.tool()
def preference_questions() -> dict:
    """Fallback for clients without interactive forms: the questions to ask the user in chat, plus current values."""
    return {"questions": QUESTIONS, "current": _prefs(), "next_step": "Ask these in chat, then call set_preferences."}


@mcp.tool()
def set_preferences(output_format: Fmt = "both", max_pages: int = 2, ats_safe: bool = True,
                    sections_to_drop: str = "", tone: Literal["concise", "balanced", "detailed"] = "balanced") -> dict:
    """Save CV preferences given in chat (fallback for clients without interactive forms)."""
    prefs = Prefs(output_format=output_format, max_pages=max_pages, ats_safe=ats_safe,
                  sections_to_drop=sections_to_drop, tone=tone).model_dump()
    config.write_json(config.prefs_path(), prefs)
    return {"status": "saved", "preferences": prefs}


# ───────────────────────── templates / preview ─────────────────────────
@mcp.tool()
def list_templates() -> list[dict]:
    """List the available CV design templates."""
    return templates.catalog()


@mcp.tool()
def preview_templates(tailored_json: str = "", template_ids: list[str] | None = None) -> list:
    """Render the user's own (tailored) content in each template and return page-1 thumbnails so they can choose.
    Leave tailored_json empty to preview the saved base CV."""
    base = schema.load_cv()
    cv = schema.merge(base, _parse_cv_json(tailored_json, "tailored_json")) if tailored_json else base
    cv = _drop_sections(cv, _prefs()["sections_to_drop"])
    out: list = ["Preview (page 1) of each template with your content. Ask the user which one they prefer."]
    with tempfile.TemporaryDirectory() as tmp:
        for tid in template_ids or list(templates.TEMPLATES):
            tpl = templates.get(tid)
            docx = str(Path(tmp) / f"{tid}.docx")
            build_docx(cv, tpl, docx)
            pdf = fit.to_pdf(docx)
            out.append(f"{tid}: {tpl.label} - {tpl.description} ({fit.page_count(pdf)} page(s) before fitting)")
            out.append(Image(data=fit.pdf_to_png(pdf), format="png"))
    return out


# ───────────────────────── verify / render ─────────────────────────
@mcp.tool()
def verify_cv(tailored_json: str) -> dict:
    """Run the safety checks without rendering: new numbers, changed employers/dates/degrees, unsupported skills."""
    base = schema.load_cv()
    merged = schema.merge(base, _parse_cv_json(tailored_json, "tailored_json"))
    return verify.verify(base, merged)


@mcp.tool()
def render_cv(tailored_json: str, template_id: str = "classic_ats", output_format: Fmt | None = None,
              max_pages: int | None = None, company: str = "", role: str = "", job_description: str = "",
              allow_unverified: bool = False) -> dict:
    """Verify, fit to the page limit, render and ATS-check the tailored CV in the chosen template.
    output_format and max_pages default to the saved preferences. Returns file paths and a report."""
    prefs = _prefs()
    fmt, pages_limit = output_format or prefs["output_format"], max_pages or prefs["max_pages"]
    tpl = templates.get(template_id)

    base = schema.load_cv()
    merged = schema.merge(base, _parse_cv_json(tailored_json, "tailored_json"))
    check = verify.verify(base, merged)
    if not check["passed"] and not allow_unverified:
        return {"status": "blocked", "problems": check["blocking"], "warnings": check["warnings"],
                "fix": "Remove or correct these items so the CV only uses facts from the original, then call render_cv again."}

    merged = _drop_sections(merged, prefs["sections_to_drop"])
    folder = config.outputs_dir() / f"{config.timestamp()}_{config.slug(company)}_{config.slug(role, 'role')}"
    folder.mkdir(parents=True)
    docx_path = str(folder / f"{config.slug(base['name'], 'cv')}_cv_{template_id}.docx")

    result = fit.fit_to_pages(merged, tpl, pages_limit, docx_path)
    final_cv, pdf_path = result["cv"], result["pdf"]
    ats = verify.ats_check(final_cv, pdf_path or docx_path)

    files = []
    if fmt in ("docx", "both"):
        files.append(docx_path)
    elif Path(docx_path).exists():
        Path(docx_path).unlink()
    if pdf_path and fmt in ("pdf", "both"):
        files.append(pdf_path)
    elif pdf_path and Path(pdf_path).exists():
        Path(pdf_path).unlink()
    elif fmt in ("pdf", "both") and not pdf_path:
        result["actions"].append("PDF requested but LibreOffice is not installed; only DOCX was produced.")
        files.append(docx_path)

    config.write_json(folder / "tailored_cv.json", final_cv)
    if job_description:
        (folder / "job_description.txt").write_text(job_description, encoding="utf-8")

    return {"status": "ok", "files": files, "folder": str(folder), "template": template_id, "pages": result["pages"],
            "fitted": result["fitted"], "fit_actions": result["actions"], "verification_warnings": check["warnings"],
            "ats_check": ats}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
