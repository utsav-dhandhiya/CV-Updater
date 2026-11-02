"""Template specs. A template is data (fonts, sizes, colors, layout flags), not code."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Template:
    id: str
    label: str
    description: str
    font: str = "Arial"
    name_size: float = 22
    title_size: float = 11
    body_size: float = 10
    heading_size: float = 11
    detail_size: float = 9
    accent: str = "000000"       # hex, used for name/heading rule
    heading_color: str = "000000"
    muted: str = "555555"
    name_align: str = "left"     # left | center
    heading_caps: bool = True
    heading_rule: bool = True
    margin_in: float = 0.75
    section_gap: float = 9       # pt before each section heading
    entry_gap: float = 5         # pt before each experience/project entry
    bullet_gap: float = 1.5
    line_spacing: float = 1.08
    skills_sep: str = " | "


TEMPLATES: dict[str, Template] = {
    "classic_ats": Template(
        id="classic_ats",
        label="Classic ATS",
        description="Single column, black on white, uppercase headings with a thin rule. Safest for applicant tracking systems.",
    ),
    "modern": Template(
        id="modern",
        label="Modern",
        description="Larger name, blue accent on headings and rule, sentence-case headings, skills separated by dots.",
        font="Calibri",
        name_size=26,
        accent="1F4E79",
        heading_color="1F4E79",
        heading_caps=False,
        heading_size=12,
        skills_sep=" · ",
        line_spacing=1.1,
    ),
    "compact": Template(
        id="compact",
        label="Compact",
        description="Dense one-page layout: smaller type, tight margins and spacing. Best when you have a lot to fit.",
        font="Arial",
        name_size=18,
        body_size=9,
        detail_size=8.5,
        heading_size=10,
        margin_in=0.55,
        section_gap=6,
        entry_gap=3,
        bullet_gap=0.5,
        line_spacing=1.0,
        name_align="center",
    ),
}


def get(template_id: str) -> Template:
    if template_id not in TEMPLATES:
        raise KeyError(f"Unknown template '{template_id}'. Available: {', '.join(TEMPLATES)}")
    return TEMPLATES[template_id]


def catalog() -> list[dict]:
    return [{"id": t.id, "label": t.label, "description": t.description, "font": t.font} for t in TEMPLATES.values()]


def as_dict(t: Template) -> dict:
    return asdict(t)
