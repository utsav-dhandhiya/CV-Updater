# CV-Automator

Tailor your CV to any job description in minutes instead of an hour.

CV-Automator is an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that works inside Claude. You import your CV once, paste a job description, and get a job-specific, ATS-friendly CV as `.docx` or `.pdf`, with every claim checked against your original CV.

> In my own testing, tailoring dropped from ~45 minutes by hand to under 2 minutes, with nearly all job-description keywords covered.

<!-- Add a demo GIF or screenshots here: ![demo](docs/demo.gif) -->

## Features

- **Import** an existing CV (`.pdf` or `.docx`) and store it as structured data
- **Analyze a job description** against your CV: which terms are covered, which are gaps, which are ambiguous
- **Tailor** your projects and bullets for each application (fresh bullets per job)
- **Anti-hallucination checks**: flags new numbers, changed employers/dates/degrees, and unsupported skills before export
- **Multiple templates** with preview thumbnails rendered from *your* content
- **Export** to `.docx`, `.pdf`, or both, fitted to a page limit and ATS-checked
- **Preferences**: tone, page limit, output format, sections to drop

## Privacy

Your files and saved CV data stay **on your own computer**; this server does not upload anything anywhere.
Note that tailoring is done by Claude, so the CV text you work with in the chat is processed by Anthropic under your own Claude account's terms and privacy settings.

## Requirements

- **Python 3.10+**
- **Claude Desktop** (or another MCP-compatible client)
- Optional, only if your PDF export or previews need it: **LibreOffice** and/or **Poppler**

## Installation

```bash
git clone https://github.com/<your-username>/CV-Automator.git
cd CV-Automator
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Connect it to Claude Desktop

1. Open Claude Desktop → **Settings → Developer → Edit Config**. This opens `claude_desktop_config.json`:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the server. Use the **full path** to the Python inside your `.venv`, and the full path to `server.py`.

**macOS / Linux**
```json
{
  "mcpServers": {
    "cv-automator": {
      "command": "/full/path/to/CV-Automator/.venv/bin/python",
      "args": ["/full/path/to/CV-Automator/server.py"]
    }
  }
}
```

**Windows** (use double backslashes)
```json
{
  "mcpServers": {
    "cv-automator": {
      "command": "C:\\full\\path\\to\\CV-Automator\\.venv\\Scripts\\python.exe",
      "args": ["C:\\full\\path\\to\\CV-Automator\\server.py"]
    }
  }
}
```

3. Save and **fully quit and reopen** Claude Desktop.
4. Start a new chat. You should see the `cv-automator` tools in the tools menu.

## How to use

1. **Set up once.** Ask Claude to import your CV and give it the file path on your computer, e.g. *"Import my CV from `/Users/me/Documents/my_cv.pdf`."* Claude extracts the text, structures it, and saves it as your base CV.
2. **Set preferences** (page limit, tone, format) when asked.
3. **For each job:** paste the job description and ask Claude to analyze the fit, tailor your CV, and preview templates.
4. **Pick a template and export.** You get a `.docx` and/or `.pdf` file. Always read the result and check the verification report before sending it.

## Troubleshooting

| Problem | Fix |
|---|---|
| Tools don't appear in Claude | Check the paths in the config are absolute and correct, then fully restart Claude Desktop. Check the MCP logs from Settings → Developer. |
| `ModuleNotFoundError` | Claude is using the wrong Python. Point `command` at the `.venv` Python, as shown above. |
| PDF text is empty or garbled | The CV may be a scanned image or have an unusual layout. Try the `.docx` version or export a fresh PDF from Word/Google Docs. |
| Output looks different in another app | Open it in Word and Google Docs and compare. Please open an issue with the details. |
| PDF export fails | Make sure LibreOffice is installed if your setup uses it. |

## Project status

Early release, built as a learning project and tested mainly on one person's CV. Expect rough edges, and please report them.

**Roadmap:** hosted multi-user version (accessible from the Claude mobile app), more templates, better parsing of multi-column CVs.

## Feedback and bugs

Please open a [GitHub Issue](../../issues) and include:
- Your OS and Python version
- What you did and the exact error message
- (If a CV failed to parse) the layout type, never the CV itself

## License

MIT, see [LICENSE](LICENSE).

## Author

Built by Utsav Dhandhiya. Contributions and suggestions welcome.
