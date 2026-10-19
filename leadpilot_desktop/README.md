# Horyalf LeadPilot B2B Desktop Companion

An independent, no-third-party-Python-dependency Windows desktop tool for preparing B2B prospects and outreach **without touching the original Etsy web analyzer**.

## What the one-click launcher does

- Opens a local Chinese-language desktop workspace.
- Opens an installed LeadPilot Start Menu shortcut if one is found, otherwise the vendor's official URL \`https://gopluxa.com/\`.
- You sign in inside the official LeadPilot app/browser. Existing sessions may remain signed in according to vendor/browser behavior.
- Provides buyer-segment search terms, outreach drafts and a CSV prospect log.
- Imports/exports CSV, deduplicates \`Company+Email\`, and records statuses (including Do not contact).
- Stores local CSV at \`%LOCALAPPDATA%\\HoryalfLeadPilot\\prospects.csv\`.

**No credentials, cookies or API keys are collected. No credits spent. No autonomous sending, scraping or login bypass.**

## Installation on Windows

1. Download the \`leadpilot_desktop\` directory from the GitHub project (or clone the repository).
2. Ensure Python 3 is installed with Tkinter: in PowerShell run \`py -3 -m tkinter\` to test GUI support.
3. Open PowerShell inside this folder and run:
   \`\`\`powershell
   powershell -ExecutionPolicy Bypass -File .\\install_desktop.ps1
   \`\`\`
4. Double-click the new **LeadPilot B2B 工作台** desktop icon.

For a temporary launcher without a shortcut, double-click \`launch.bat\`.

## LeadPilot account connection

First version opens the authentic installed client or the official website. **It does not programmatically read or synchronize your account.** There is no documented official API credential/authentication flow in the provided LeadPilot manual. To support genuine automatic sync, obtain vendor API documentation and explicit account authorization, then implement that integration separately. Do not enter your password into this companion.

## CSV columns

Use the LeadPilot export or a CSV containing a \`Company\` or \`公司\` column. Optional columns: Country, Contact, Email, Segment, Status, Notes. Email addresses stay only on this PC unless you manually export and share the CSV. Do not commit exported leads or personal contact data.

## Validation

\`\`\`powershell
py -3 -m unittest discover -s leadpilot_desktop/tests -v
\`\`\`

Desktop shortcut creation and Windows Start Menu detection must be validated on your actual Windows computer.
