"""End-to-end over the real MCP protocol (in-process client): tools, prompt, resource, elicitation, images."""
import asyncio, json, os, tempfile
from pathlib import Path

os.environ["CV_UPDATER_HOME"] = tempfile.mkdtemp(prefix="cvu_e2e_")

from mcp import Client  # noqa: E402
from mcp_types import ElicitResult  # noqa: E402

from cv_updater.server import mcp  # noqa: E402

EX = Path(__file__).resolve().parent.parent / "examples"


async def accept_form(context, params):
    return ElicitResult(action="accept", content={"output_format": "pdf", "max_pages": 1, "ats_safe": True,
                                                  "sections_to_drop": "achievements", "tone": "concise"})


async def main():
    async with Client(mcp, elicitation_callback=accept_form) as c:
        tools = [t.name for t in (await c.list_tools()).tools]
        print("tools:", tools)
        r = await c.call_tool("save_cv_data", {"cv_json": (EX / "cv_data.json").read_text()})
        print("save:", r.content[0].text[:80])
        r = await c.call_tool("collect_preferences", {})
        print("prefs:", r.content[0].text[:200])
        r = await c.call_tool("preview_templates", {"tailored_json": (EX / "tailored_azure_ml.json").read_text()})
        print("preview blocks:", [b.type for b in r.content])
        r = await c.call_tool("render_cv", {"tailored_json": (EX / "tailored_azure_ml.json").read_text(),
                                            "template_id": "modern", "company": "Acme", "role": "ML Engineer"})
        print("render:", r.content[0].text[:600])
        r = await c.call_tool("render_cv", {"tailored_json": json.dumps({"summary": "Boosted F1 by 37%."})})
        print("blocked:", r.content[0].text[:200])
        p = await c.get_prompt("tailor_cv", {"job_description": "Azure RAG PyTorch"})
        print("prompt chars:", len(p.messages[0].content.text))
        res = await c.read_resource("cv://profile")
        print("resource ok:", "Utsav" in res.contents[0].text)

asyncio.run(main())
