# Archon MCP Helper (PowerShell)

Use this helper to streamline Archon MCP commands or print ready‑to‑run snippets with the project ID prefilled.

- Load helper: `. .\\scripts\\archon.ps1`
- Check availability: `Test-ArchonMcpAvailable`
- Default project: `b92eed44-93e0-49d4-9cd5-011893b43edd`
  - Override: `Set-ArchonProjectId -ProjectId <uuid>` or set `$env:ARCHON_PROJECT_ID` before loading

## Common Commands

```powershell
# Tasks
Get-ArchonTasks -FilterBy status -FilterValue todo
Get-ArchonTask -TaskId "9da7c5c3-4bd4-44db-864e-b4f93f74319d"
Update-ArchonTask -TaskId "9da7c5c3-4bd4-44db-864e-b4f93f74319d" -Status doing -Description "Starting work"

# Documentation
List-ArchonDocuments
Get-ArchonDocument -DocId "1d93e70a-1a03-459f-86b3-600caf84d0ef"

# RAG & code search
Perform-ArchonRag -Query "NetworkX to Neo4j import process"
Search-ArchonCode -Query "Streamlit Neo4j integration"
```

## Notes
- If MCP tools are not detected in your shell, the helper prints the exact snippet to paste into your MCP‑enabled console.
- Works with Windows PowerShell and PowerShell Core; for other shells, use PowerShell (`pwsh`) to dot‑source the script.
