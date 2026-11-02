"""CV dict + Template -> .docx. One rendering path; PDF and PNG are derived from the .docx."""
from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .templates import Template

SECTION_TITLES = {
    "summary": "Summary",
    "skills": "Skills",
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "certifications": "Certifications",
    "achievements": "Achievements & Awards",
}
ORDER = ["summary", "skills", "experience", "projects", "education", "certifications", "achievements"]


def _rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_.upper())


def _run(par, text, size, font, bold=False, italic=False, color=None):
    r = par.add_run(text)
    r.font.size = Pt(size)
    r.font.name = font
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    r.bold, r.italic = bold, italic
    if color:
        r.font.color.rgb = _rgb(color)
    return r


def _bottom_rule(par, color: str):
    pPr = par._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", color)):
        b.set(qn(f"w:{k}"), v)
    borders.append(b)
    pPr.append(borders)


class Builder:
    def __init__(self, tpl: Template, spacing_scale: float = 1.0, font_delta: float = 0.0):
        self.t, self.s, self.d = tpl, spacing_scale, font_delta
        self.doc = Document()
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)  # A4
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Inches(tpl.margin_in))
        self.text_width = Inches(8.27 - 2 * tpl.margin_in)
        normal = self.doc.styles["Normal"]
        normal.font.name, normal.font.size = tpl.font, Pt(self._sz(tpl.body_size))

    # -- helpers
    def _sz(self, size: float) -> float:
        return max(7.0, size + self.d)

    def _par(self, before=0.0, after=0.0, align=None, keep_next=False):
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before, pf.space_after = Pt(before * self.s), Pt(after * self.s)
        pf.line_spacing = max(1.0, self.t.line_spacing * (0.9 + 0.1 * self.s))
        pf.keep_with_next = keep_next
        if align:
            p.alignment = align
        return p

    def _tabbed(self, left_runs, right_text, size, before=0.0, bold_right=False, color=None):
        p = self._par(before=before, keep_next=True)
        p.paragraph_format.tab_stops.add_tab_stop(self.text_width, WD_TAB_ALIGNMENT.RIGHT)
        for text, bold, italic, c in left_runs:
            _run(p, text, size, self.t.font, bold, italic, c)
        if right_text:
            _run(p, "\t" + right_text, self.t.detail_size + self.d, self.t.font, bold_right, False, color or self.t.muted)
        return p

    def _bullet(self, text: str):
        p = self.doc.add_paragraph(style="List Bullet")
        pf = p.paragraph_format
        pf.space_before, pf.space_after = Pt(self.t.bullet_gap * self.s), Pt(0)
        pf.line_spacing = max(1.0, self.t.line_spacing * (0.9 + 0.1 * self.s))
        pf.left_indent, pf.first_line_indent = Inches(0.22), Inches(-0.18)
        _run(p, text, self._sz(self.t.body_size), self.t.font)

    def _heading(self, text: str):
        p = self._par(before=self.t.section_gap, after=2, keep_next=True)
        _run(p, text.upper() if self.t.heading_caps else text, self._sz(self.t.heading_size), self.t.font,
             bold=True, color=self.t.heading_color)
        if self.t.heading_rule:
            _bottom_rule(p, self.t.accent)

    # -- sections
    def header(self, cv: dict):
        t = self.t
        align = WD_ALIGN_PARAGRAPH.CENTER if t.name_align == "center" else WD_ALIGN_PARAGRAPH.LEFT
        p = self._par(align=align)
        _run(p, cv["name"], self._sz(t.name_size), t.font, bold=True, color=t.accent)
        if cv.get("title"):
            _run(self._par(before=1, align=align), cv["title"], self._sz(t.title_size), t.font, bold=True, color=t.muted)
        c = cv.get("contact", {})
        bits = [c.get(k) for k in ("phone", "email", "linkedin", "location") if c.get(k)]
        if bits:
            _run(self._par(before=2, after=2, align=align), "  |  ".join(bits), self._sz(t.detail_size), t.font, color=t.muted)

    def summary(self, text: str):
        self._heading(SECTION_TITLES["summary"])
        _run(self._par(), text, self._sz(self.t.body_size), self.t.font)

    def skills(self, skills: list[str]):
        self._heading(SECTION_TITLES["skills"])
        _run(self._par(), self.t.skills_sep.join(skills), self._sz(self.t.body_size), self.t.font)

    def experience(self, items: list[dict]):
        self._heading(SECTION_TITLES["experience"])
        for e in items:
            self._tabbed([(e["company"], True, False, None)], e.get("location", ""), self._sz(self.t.body_size + 0.5),
                         before=self.t.entry_gap)
            dates = " - ".join(x for x in (e.get("start"), e.get("end")) if x)
            self._tabbed([(e.get("role", ""), False, True, None)], dates, self._sz(self.t.body_size))
            for b in e.get("bullets", []):
                self._bullet(b)

    def projects(self, items: list[dict]):
        self._heading(SECTION_TITLES["projects"])
        for pr in items:
            p = self._par(before=self.t.entry_gap, keep_next=True)
            _run(p, pr["name"], self._sz(self.t.body_size + 0.5), self.t.font, bold=True)
            if pr.get("tech"):
                _run(p, "  |  " + pr["tech"], self._sz(self.t.detail_size), self.t.font, italic=True, color=self.t.muted)
            for b in pr.get("bullets", []):
                self._bullet(b)

    def education(self, items: list[dict]):
        self._heading(SECTION_TITLES["education"])
        for ed in items:
            self._tabbed([(ed["institution"], True, False, None)], ed.get("location", ""), self._sz(self.t.body_size + 0.5),
                         before=self.t.entry_gap)
            self._tabbed([(ed.get("degree", ""), False, False, None)], ed.get("year", ""), self._sz(self.t.body_size))

    def certifications(self, items: list[dict]):
        self._heading(SECTION_TITLES["certifications"])
        for c in items:
            p = self._par(before=self.t.entry_gap, keep_next=True)
            _run(p, c["name"], self._sz(self.t.body_size + 0.5), self.t.font, bold=True)
            meta = " | ".join(x for x in (c.get("issuer"), c.get("date"),
                                         f"Credential ID: {c['credential_id']}" if c.get("credential_id") else "") if x)
            if meta:
                _run(self._par(), meta, self._sz(self.t.detail_size), self.t.font, color=self.t.muted)

    def achievements(self, items: list[dict]):
        self._heading(SECTION_TITLES["achievements"])
        for a in items:
            p = self._par(before=self.t.entry_gap)
            _run(p, a["title"], self._sz(self.t.body_size), self.t.font, bold=True)
            if a.get("description"):
                _run(p, " - " + a["description"], self._sz(self.t.body_size), self.t.font)


def build_docx(cv: dict, tpl: Template, path: str, spacing_scale: float = 1.0, font_delta: float = 0.0) -> str:
    b = Builder(tpl, spacing_scale, font_delta)
    b.header(cv)
    for key in ORDER:
        val = cv.get(key)
        if val:
            getattr(b, key)(val)
    b.doc.core_properties.author = cv["name"]
    b.doc.core_properties.title = f"{cv['name']} - CV"
    b.doc.save(path)
    return path
