"""Plain-Python tests: import and call the server functions directly (no stdio needed)."""
import json
import os
import tempfile
from pathlib import Path

os.environ["CV_UPDATER_HOME"] = tempfile.mkdtemp(prefix="cvu_")

from cv_updater import analysis, fit, schema, server, templates, verify  # noqa: E402

EX = Path(__file__).resolve().parent.parent / "examples"
BASE = json.loads((EX / "cv_data.json").read_text())
TAILORED = json.loads((EX / "tailored_azure_ml.json").read_text())
JD = """Design, develop and deploy large language models using AIML on Microsoft Azure. Retrieval augmented generation.
2-6 years of experience with TensorFlow or PyTorch. Large datasets on Azure."""


def test_save_and_backup():
    server.save_cv_data(json.dumps(BASE))
    second = server.save_cv_data(json.dumps(BASE))
    assert second["backup"]


def test_gap_report():
    r = analysis.gap_report(BASE, JD)
    assert "PyTorch" in r["gaps"] and "TensorFlow" in r["gaps"]
    assert "RAG" in r["already_in_cv"] and "aiml" in r["ambiguous_terms"]


def test_verify_blocks_invented_number_and_job_change():
    bad = {"summary": "Cut latency by 73% and led 12 engineers."}
    assert not verify.verify(BASE, schema.merge(BASE, bad))["passed"]
    exp = json.loads(json.dumps(BASE["experience"]))
    exp[0]["role"] = "Senior AI Engineer"
    assert not verify.verify(BASE, schema.merge(BASE, {"experience": exp}))["passed"]
    assert verify.verify(BASE, schema.merge(BASE, TAILORED))["passed"]


def test_unsupported_skill_warns():
    out = verify.verify(BASE, schema.merge(BASE, {"skills": ["Python", "PyTorch"]}))
    assert any("PyTorch" in w for w in out["warnings"])


def test_render_all_templates_fit_and_ats():
    for tid in templates.TEMPLATES:
        r = server.render_cv(json.dumps(TAILORED), template_id=tid, max_pages=2, company="Acme", role="ML Engineer",
                             job_description=JD)
        assert r["status"] == "ok", r
        assert r["pages"] <= 2 and r["fitted"], r
        assert r["ats_check"]["passed"], r["ats_check"]
        assert all(Path(f).exists() for f in r["files"])
        print(tid, r["pages"], "pages", r["fit_actions"])


def test_one_page_limit_trims():
    r = server.render_cv(json.dumps(TAILORED), template_id="classic_ats", max_pages=1, output_format="pdf")
    assert r["pages"] == 1 and r["fitted"], r
    assert r["fit_actions"], "expected spacing/font/bullet adjustments"
    print(r["fit_actions"])


def test_render_blocked_on_invented_number():
    r = server.render_cv(json.dumps({"summary": "Improved accuracy by 91%."}))
    assert r["status"] == "blocked"


def test_preview_returns_images():
    out = server.preview_templates(json.dumps(TAILORED))
    imgs = [o for o in out if not isinstance(o, str)]
    assert len(imgs) == len(templates.TEMPLATES)


if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-x", "-q", "-s"]))
