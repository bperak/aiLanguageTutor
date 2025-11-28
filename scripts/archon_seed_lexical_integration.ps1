# Seed Archon MCP with Lexical Integration document and follow-up tasks
# Usage: pwsh -File .\scripts\archon_seed_lexical_integration.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. $PSScriptRoot/archon.ps1

$projectId = Get-ArchonProjectId
Write-Host "[Archon] Using project: $projectId"

# Build document content (JSON string)
$docContent = @'
{
  "overview": "2D/3D lexical visualization, level-based lessons, readability scoring.",
  "backend": {
    "endpoints": [
      "GET /api/v1/lexical/graph",
      "GET /api/v1/lexical/lessons/seed",
      "POST /api/v1/lexical/lessons/generate",
      "POST /api/v1/lexical/lessons/attempt",
      "POST /api/v1/lexical/readability"
    ],
    "services": [
      "app/services/lexical_lessons_service.py",
      "app/services/readability_service.py"
    ]
  },
  "frontend": {
    "pages": [
      "src/app/lexical/graph/page.tsx",
      "src/app/lexical/lessons/page.tsx"
    ],
    "components": [
      "LexicalGraph3D.tsx",
      "LexicalGraph2D.tsx"
    ]
  },
  "visuals": {
    "node_color_by": ["domain", "pos", "level"],
    "link_width_by": "synonym_strength",
    "expand_on_click": true
  },
  "readability": {
    "optional": true,
    "deps": ["jreadability", "fugashi"],
    "fallback": "available=false"
  },
  "attempt_logging": {
    "uses": "ConversationSession/Message",
    "requires_auth": true
  },
  "env": {
    "frontend": "NEXT_PUBLIC_API_BASE_URL",
    "backend": ["OPENAI_API_KEY", "GEMINI_API_KEY"]
  },
  "next_steps": [
    "Legends & color palette by domain/POS",
    "Auth wiring for attempt logging",
    "Sampling for dense neighborhoods",
    "API tests for new endpoints",
    "Persist dedicated lesson attempts schema"
  ]
}
'@

Write-Host "[Archon] Creating document: Lexical Features Integration"
Invoke-Archon -Tool 'mcp_archon_create_document' -Params @{
  title = 'Lexical Features Integration'
  document_type = 'design'
  tags = 'lexical,visualization,lessons,readability'
  content = $docContent
}

Write-Host "[Archon] Creating tasks"
Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'Lexical Graph – Legends & Palette'
  description = 'Add domain/POS legends, consistent color palette, and link color scale that matches relation strength.'
  assignee = 'AI IDE Agent'
  task_order = '11'
  feature = 'lexical-visualization'
}

Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'Lexical Graph – Expansion Performance & Sampling'
  description = 'Server-side sampling for dense nodes; client throttle; depth=2 safeguards; regression checks.'
  assignee = 'AI IDE Agent'
  task_order = '10'
  feature = 'lexical-visualization'
}

Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'Lexical Lessons – Attempt Logging with Auth'
  description = 'Attach JWT/cookie auth to POST /lexical/lessons/attempt; error handling UX; confirm entries in Postgres.'
  assignee = 'AI IDE Agent'
  task_order = '9'
  feature = 'lexical-lessons'
}

Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'Readability – Dependencies & Feature Flag'
  description = 'Provision jreadability+fugashi, CI check, env flag to disable; UX note when unavailable.'
  assignee = 'AI IDE Agent'
  task_order = '8'
  feature = 'readability'
}

Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'API Tests – Lexical Endpoints'
  description = 'Add pytest coverage for /lexical/graph, /lessons/seed, /lessons/generate, /readability, /lessons/attempt.'
  assignee = 'AI IDE Agent'
  task_order = '8'
  feature = 'testing'
}

Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'Lesson Attempts – Persistence Design'
  description = 'Decide between dedicated lesson_attempts table vs conversation reuse; analytics queries; dashboard view.'
  assignee = 'AI IDE Agent'
  task_order = '7'
  feature = 'analytics'
}

Invoke-Archon -Tool 'mcp_archon_create_task' -Params @{
  title = 'Docs – Link Lexical Features & Archon Helper'
  description = 'Link docs/LEXICAL_FEATURES.md in README; reference docs/ARCHON_HELPER.md in Archon section.'
  assignee = 'User'
  task_order = '6'
  feature = 'documentation'
}

Write-Host "[Archon] Done. If MCP tools were not detected, the script printed the exact snippets to run in your MCP console."

