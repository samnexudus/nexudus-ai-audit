# Requirements

## Nexudus CLI
The audit uses the Nexudus CLI to fetch all account data.

Install via .NET:
```bash
dotnet tool install --global nexudus-cli
```

Then authenticate:
```bash
nexudus login
```

Minimum version: check you're on the latest with `nexudus --version`.

## GitHub CLI
Required for publishing reports to GitHub Pages.

Install via Homebrew (macOS):
```bash
brew install gh
```

Then authenticate:
```bash
gh auth login
```

## Python
Python 3.9 or later. No third-party packages — the audit uses the standard library only.

Check your version:
```bash
python3 --version
```

## Nexudus MCP Server (optional)
Not required to run the audit, but useful for exploring Nexudus data during development. Connect via Claude Code settings.

---

## Running the audit

```bash
cd "AI Agent Audit"
python3 audit.py
```

To publish the report to GitHub Pages:
```bash
python3 audit.py --publish
```

Other options:
```
--business <id>    Audit a specific business ID (defaults to your logged-in account)
--output <dir>     Save the HTML report to a custom directory
--no-html          Terminal output only, no HTML report
--json             Output results as JSON
```

Reports are saved to `Reports/<Location Name>/<date>.html`.
