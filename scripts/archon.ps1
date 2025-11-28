# Archon MCP Helper for AI Language Tutor
#
# Usage:
#   # Load in current shell
#   . ./scripts/archon.ps1
#
#   # Examples
#   Get-ArchonTasks -FilterBy status -FilterValue todo
#   Get-ArchonTask -TaskId "9da7c5c3-4bd4-44db-864e-b4f93f74319d"
#   Update-ArchonTask -TaskId "9da7c5c3-4bd4-44db-864e-b4f93f74319d" -Status doing
#   Perform-ArchonRag -Query "Google Cloud Speech API integration"
#   Search-ArchonCode -Query "Streamlit Neo4j integration"
#   List-ArchonDocuments
#   Get-ArchonDocument -DocId "1d93e70a-1a03-459f-86b3-600caf84d0ef"

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Default project id from docs; can be overridden by env ARCHON_PROJECT_ID or Set-ArchonProjectId
$script:ARCHON_PROJECT_ID = if ($env:ARCHON_PROJECT_ID) { $env:ARCHON_PROJECT_ID } else { 'b92eed44-93e0-49d4-9cd5-011893b43edd' }

function Get-ArchonProjectId {
  <#
    .SYNOPSIS
    Returns the current Archon project id used by wrappers.
  #>
  return $script:ARCHON_PROJECT_ID
}

function Set-ArchonProjectId {
  <#
    .SYNOPSIS
    Overrides the Archon project id for this session.
  #>
  param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId
  )
  $script:ARCHON_PROJECT_ID = $ProjectId
}

function Test-ArchonMcpAvailable {
  <#
    .SYNOPSIS
    Checks if MCP Archon tools are available in this shell.
  #>
  $tools = @(
    'mcp_archon_list_tasks',
    'mcp_archon_get_task',
    'mcp_archon_update_task'
  )
  foreach ($t in $tools) {
    if (Get-Command $t -ErrorAction SilentlyContinue) { return $true }
  }
  return $false
}

function Invoke-Archon {
  <#
    .SYNOPSIS
    Core invoker: runs an MCP Archon tool if available, else prints a ready-to-run snippet.

    .PARAMETER Tool
    Tool name, e.g. mcp_archon_list_tasks

    .PARAMETER Params
    Hashtable of parameters (converted to Archon call syntax).
  #>
  param(
    [Parameter(Mandatory=$true)][string]$Tool,
    [hashtable]$Params
  )

  if (-not $Params) { $Params = @{} }
  if (-not $Params.ContainsKey('project_id')) {
    $Params['project_id'] = Get-ArchonProjectId
  }

  # Build key='value' pairs; double any embedded single quotes in values.
  $pairs = foreach ($k in $Params.Keys) {
    $v = [string]$Params[$k]
    $v = $v -replace "'", "''"
    "$k='$v'"
  }
  $call = "$Tool(" + ($pairs -join ', ') + ")"

  $cmd = Get-Command $Tool -ErrorAction SilentlyContinue
  if ($cmd) {
    try { Invoke-Expression $call } catch { Write-Warning "Failed to execute '$Tool'. Printing snippet. Error: $($_.Exception.Message)"; Write-Host $call }
  } else {
    Write-Warning "Archon MCP tools not detected in this shell. Printing snippet for your MCP-enabled console:"
    Write-Host $call
  }
}

function Get-ArchonTasks {
  <#
    .SYNOPSIS
    Lists tasks; supports simple filtering.

    .PARAMETER FilterBy
    One of: status | project | assignee | feature

    .PARAMETER FilterValue
    Value for FilterBy.
  #>
  param(
    [ValidateSet('status','project','assignee','feature')]
    [string]$FilterBy,
    [string]$FilterValue
  )
  $p = @{}
  if ($FilterBy -and $FilterValue) {
    $p['filter_by'] = $FilterBy
    $p['filter_value'] = $FilterValue
  }
  Invoke-Archon -Tool 'mcp_archon_list_tasks' -Params $p
}

function Get-ArchonTask {
  <#
    .SYNOPSIS
    Gets task details by id.
  #>
  param(
    [Parameter(Mandatory=$true)][string]$TaskId
  )
  Invoke-Archon -Tool 'mcp_archon_get_task' -Params @{ task_id = $TaskId }
}

function Update-ArchonTask {
  <#
    .SYNOPSIS
    Updates task status and/or description.
  #>
  param(
    [Parameter(Mandatory=$true)][string]$TaskId,
    [ValidateSet('todo','doing','review','done')]
    [string]$Status,
    [string]$Description
  )
  $p = @{ task_id = $TaskId }
  if ($Status) { $p['status'] = $Status }
  if ($Description) { $p['description'] = $Description }
  Invoke-Archon -Tool 'mcp_archon_update_task' -Params $p
}

function List-ArchonDocuments {
  <#
    .SYNOPSIS
    Lists documents for the project.
  #>
  Invoke-Archon -Tool 'mcp_archon_list_documents' -Params @{}
}

function Get-ArchonDocument {
  <#
    .SYNOPSIS
    Gets document details by id.
  #>
  param(
    [Parameter(Mandatory=$true)][string]$DocId
  )
  Invoke-Archon -Tool 'mcp_archon_get_document' -Params @{ doc_id = $DocId }
}

function Perform-ArchonRag {
  <#
    .SYNOPSIS
    Performs a RAG query over the project knowledge base.
  #>
  param(
    [Parameter(Mandatory=$true)][string]$Query
  )
  Invoke-Archon -Tool 'mcp_archon_perform_rag_query' -Params @{ query = $Query }
}

function Search-ArchonCode {
  <#
    .SYNOPSIS
    Searches code examples in the knowledge base.
  #>
  param(
    [Parameter(Mandatory=$true)][string]$Query
  )
  Invoke-Archon -Tool 'mcp_archon_search_code_examples' -Params @{ query = $Query }
}

Write-Host "[Archon] Helper loaded. ProjectId=$(Get-ArchonProjectId). Use Set-ArchonProjectId to change."

