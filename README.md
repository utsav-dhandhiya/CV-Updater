# CV-Updater

Tailor your CV to any job description in minutes instead of an hour.

CV-Updater is an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that works inside Claude. Your CV is stored once as structured JSON; for each job, Claude rewrites the content and the server keeps it honest, fits it to your page limit, and renders it in the template you choose as `.docx` and/or `.pdf`.

> In my own testing, tailoring dropped from ~45 minutes by hand to under 2 minutes, with nearly all job-description keywords covered.

<!-- Add a demo GIF or screenshots: ![demo](docs/demo.gif) -->

## Features

- **Import** an existing CV (`.pdf` or `.docx`) and store it as structured data
- **Gap analysis** of a job description against your CV (covered, missing, ambiguous terms)
- **Fresh, tailored bullets** for every application
- **Anti-hallucination checks** that block invented numbers and changed employers, roles, dates, degrees or certifications, and warn about unsupported skills
- **Templates** with page-1 previews rendered from *your* content
- **Page-fit engine** and **ATS check** built into export
- **Preferences**: tone, page limit, output format, sections to drop

## Privacy

Your CV data, backups and generated files are stored **on your own computer** (default `~/.cv_updater`); this server uploads nothing.
Tailoring is done by Claude, so the CV text you discuss in the chat is processed by Anthropic under your own Claude account's terms and privacy settings.

## Requirements

- **Python 3.10+**
- **Claude Desktop** (or another MCP client that supports MCP v2 servers)
- **LibreOffice**: needed for PDF output, template previews and page-fit. Without it the server still starts, but those features are unavailable.
  - macOS: `brew install --cask libreoffice`
  - Ubuntu/Debian: `sudo apt install libreoffice`
  - Windows: install from [libreoffice.org](https://www.libreoffice.org) and make sure `soffice` is on your `PATH` (usually `C:\Program Files\LibreOffice\program`)

## Installation

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -e .
```

This installs the `cv-updater` command inside your virtual environment.

## Connect to Claude Desktop

1. Open Claude Desktop → **Settings → Developer → Edit Config**. This opens `claude_desktop_config.json`:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the server, using the **full path** to the `cv-updater` command inside your `.venv`.

**macOS / Linux**
```json
{
  "mcpServers": {
    "cv-updater": {
      "command": "/full/path/to/<repo-name>/.venv/bin/cv-updater"
    }
  }
}
```

**Windows** (double backslashes)
```json
{
  "mcpServers": {
    "cv-updater": {
      "command": "C:\\full\\path\\to\\<repo-name>\\.venv\\Scripts\\cv-updater.exe"
    }
  }
}
```

Optional: store your data somewhere else by adding `"env": { "CV_UPDATER_HOME": "/path/to/data_dir" }` next to `command`.

3. Save, then **fully quit and reopen** Claude Desktop. The `cv-updater` tools should appear in a new chat.

Your data lives in `CV_UPDATER_HOME` (default `~/.cv_updater`): `cv_data.json`, `preferences.json`, `backups/`, `outputs/`. Generated CVs are saved in `outputs/`.

## How to use

1. **Import your CV once.** Ask Claude to import it and give the file path, e.g. *"Import my CV from `/Users/me/Documents/my_cv.pdf`."* Claude extracts the text, structures it with the `parse_cv_to_json` prompt, and saves it with `save_cv_data`.
   (Quick trial: copy `examples/cv_data.json` to `~/.cv_updater/cv_data.json`.)
2. **Tailor for a job.** Use the `tailor_cv` prompt and paste the job description. It runs `analyze_job` (gap report), asks about gaps, then collects preferences (an interactive form, or a chat fallback).
3. **Preview templates** with your own content, then pick one.
4. **Export.** `render_cv` verifies the content, fits it to your page limit, renders `.docx`/`.pdf`, and runs an ATS check. Always read the result before sending it.

## Safety checks (inside `render_cv`, also available as `verify_cv`)

- **Blocking:** any number not in the original CV; any changed company, role, dates, degree, school or certification.
- **Warning:** skills with no trace in the original CV (rewording is fine, invention is not).
- **ATS check:** name first, email intact, section headings present and in order.
- **Fit engine:** tightens spacing, then font size (down to -1pt), then drops the last bullet of the longest entry. Write bullets most-relevant-first; everything changed is reported.

## Add a template

Add a `Template(...)` entry in `src/cv_updater/templates.py`. No other code changes are needed.

## Tools, prompts, resources

- Tools: `import_cv`, `save_cv_data`, `analyze_job`, `collect_preferences`, `preference_questions`, `set_preferences`, `list_templates`, `preview_templates`, `verify_cv`, `render_cv`
- Prompts: `parse_cv_to_json`, `tailor_cv`
- Resources: `cv://profile`, `cv://templates`

## Tests

```bash
pip install pytest
python tests/test_pipeline.py     # direct function calls
python tests/e2e_protocol.py      # real MCP protocol, in-process client
```
LibreOffice is needed for the preview and fit tests.

## Troubleshooting

| Problem | Fix |
|---|---|
| Tools don't appear in Claude | Use the absolute path to `cv-updater` in the config, then fully restart Claude Desktop. Check the MCP logs under Settings → Developer. |
| PDF output, previews or page-fit unavailable | LibreOffice isn't installed or `soffice` isn't on your `PATH`. |
| PDF text is empty or garbled | The CV may be a scanned image (no OCR support) or have an unusual layout. Try the `.docx`, or export a fresh PDF from Word/Google Docs. |
| Output looks different in another app | Open it in Word and Google Docs and compare, then open an issue. |

## Known limits

Born-digital PDFs only (no OCR). A4 only. The design of your *old* CV is not extracted; you pick a template. The skill-detection vocabulary in `analysis.py` is a starter list; extend it.

## Roadmap

Hosted multi-user version (usable from the Claude mobile app), more templates, better parsing of multi-column CVs.

## Feedback and bugs

Please open a GitHub Issue with your OS, Python version, what you did, and the exact error message. If a CV failed to parse, describe its layout; never attach the CV itself.

## License

MIT, see [LICENSE](LICENSE).

## Author

Built by Utsav Dhandhiya. Suggestions and contributions welcome.
