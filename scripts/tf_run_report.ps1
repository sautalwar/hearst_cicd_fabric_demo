#requires -Version 5.1
<#
.SYNOPSIS
  Turns a Terraform plan (terraform show -json) into a readable HTML run report.
.DESCRIPTION
  Pure PowerShell (no extra tools) so the customer needs nothing installed. Groups resources
  by action (create/update/delete/read) and shows a dependency-ordered "what runs when" view.
.PARAMETER PlanJsonPath
  Path to the JSON produced by: terraform show -json plan.tfplan > plan.json
.PARAMETER OutHtml
  Output HTML file path.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$PlanJsonPath,
  [string]$OutHtml = "run-report.html"
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $PlanJsonPath)) { throw "Plan JSON not found: $PlanJsonPath" }
$plan    = Get-Content -Raw -Path $PlanJsonPath | ConvertFrom-Json
$changes = @($plan.resource_changes)

function Enc([string]$s) {
  if ($null -eq $s) { return "" }
  return $s.Replace('&','&amp;').Replace('<','&lt;').Replace('>','&gt;')
}

# Bucket by action
$create = @(); $update = @(); $delete = @(); $read = @(); $noop = @()
foreach ($rc in $changes) {
  $a = @($rc.change.actions)
  if     ($a -contains 'create' -and $a -contains 'delete') { $update += $rc }   # replace
  elseif ($a -contains 'create') { $create += $rc }
  elseif ($a -contains 'update') { $update += $rc }
  elseif ($a -contains 'delete') { $delete += $rc }
  elseif ($a -contains 'read')   { $read   += $rc }
  else                           { $noop   += $rc }
}

# Logical deployment order (by resource type)
$phases = @(
  @{ name = '1 - Foundation';        types = @('azurerm_resource_group') },
  @{ name = '2 - Identity (Entra)';  types = @('azuread_application','azuread_service_principal','azuread_application_password') },
  @{ name = '3 - Key Vault + RBAC';  types = @('azurerm_key_vault','azurerm_role_assignment','azurerm_key_vault_secret') },
  @{ name = '4 - Fabric capacity';   types = @('azurerm_fabric_capacity') },
  @{ name = '5 - Workspaces + roles'; types = @('fabric_workspace','fabric_workspace_role_assignment') },
  @{ name = '6 - Deployment pipeline'; types = @('fabric_deployment_pipeline') },
  @{ name = '7 - Git integration (optional)'; types = @('fabric_workspace_git') },
  @{ name = '8 - Example workload';  types = @('fabric_lakehouse','fabric_warehouse','fabric_notebook','fabric_data_pipeline') }
)

$ts = Get-Date -Format "yyyy-MM-dd HH:mm"
$total = $changes.Count

$sb = New-Object System.Text.StringBuilder
[void]$sb.Append(@"
<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Terraform Run Report - Hearst Fabric CI/CD</title>
<style>
  body{margin:0;background:#0f1420;color:#e9eef7;font:15px/1.6 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
  .wrap{max-width:1000px;margin:0 auto;padding:30px 22px 70px}
  h1{font-size:25px;margin:0 0 4px}
  .meta{color:#a3b4cd;font-size:13px;margin-bottom:18px}
  .cards{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0 8px}
  .card{flex:1 1 150px;background:#1b2438;border:1px solid #2a3656;border-radius:12px;padding:14px}
  .card .n{font-size:26px;font-weight:700}
  .card .l{color:#a3b4cd;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  .create .n{color:#43d39e} .update .n{color:#ffc24b} .delete .n{color:#ff7a7a} .read .n{color:#5aa9ff}
  h2{font-size:18px;margin:28px 0 10px;border-bottom:1px solid #2a3656;padding-bottom:6px}
  .phase{background:#161d2e;border:1px solid #2a3656;border-radius:10px;margin:10px 0;overflow:hidden}
  .phase h3{margin:0;padding:10px 14px;background:#1b2438;font-size:14px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:7px 12px;border-bottom:1px solid #233049}
  th{color:#a3b4cd;font-weight:600}
  code{background:#0c1322;border:1px solid #2a3656;border-radius:4px;padding:1px 6px;color:#bcd2ff;font-size:12px}
  .pill{font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px}
  .p-create{color:#43d39e;background:#11271f;border:1px solid #2c5a48}
  .p-update{color:#ffc24b;background:#241d0e;border:1px solid #5a4a1f}
  .p-delete{color:#ff7a7a;background:#251111;border:1px solid #5a2c2c}
  .empty{color:#7d8aa3;font-style:italic;padding:8px 14px}
  footer{margin-top:30px;color:#7d8aa3;font-size:12px;border-top:1px solid #2a3656;padding-top:14px}
</style></head><body><div class="wrap">
<h1>Terraform Run Report</h1>
<div class="meta">Hearst Fabric CI/CD &middot; generated $ts &middot; source: plan.tfplan (terraform show -json)</div>
<div class="cards">
  <div class="card create"><div class="n">$($create.Count)</div><div class="l">to create</div></div>
  <div class="card update"><div class="n">$($update.Count)</div><div class="l">to change</div></div>
  <div class="card delete"><div class="n">$($delete.Count)</div><div class="l">to destroy</div></div>
  <div class="card read"><div class="n">$($read.Count)</div><div class="l">data reads</div></div>
  <div class="card"><div class="n">$total</div><div class="l">total tracked</div></div>
</div>
<p style="color:#a3b4cd">This report reflects a <strong>plan</strong> (nothing was created). Resources are grouped below in the order Terraform will build them.</p>
<h2>Deployment order (what runs when)</h2>
"@)

foreach ($ph in $phases) {
  $items = $create | Where-Object { $ph.types -contains $_.type }
  [void]$sb.Append("<div class='phase'><h3>Phase $($ph.name)</h3>")
  if ($items.Count -eq 0) {
    [void]$sb.Append("<div class='empty'>No resources in this phase.</div>")
  } else {
    [void]$sb.Append("<table><tr><th>Action</th><th>Type</th><th>Address</th></tr>")
    foreach ($it in $items) {
      [void]$sb.Append("<tr><td><span class='pill p-create'>create</span></td><td><code>$(Enc $it.type)</code></td><td>$(Enc $it.address)</td></tr>")
    }
    [void]$sb.Append("</table>")
  }
  [void]$sb.Append("</div>")
}

# Any create resources not matched by a phase
$matched = @(); foreach ($ph in $phases) { $matched += ($create | Where-Object { $ph.types -contains $_.type }) }
$other = $create | Where-Object { $matched -notcontains $_ }
if ($other.Count -gt 0) {
  [void]$sb.Append("<div class='phase'><h3>Phase 9 - Other</h3><table><tr><th>Action</th><th>Type</th><th>Address</th></tr>")
  foreach ($it in $other) { [void]$sb.Append("<tr><td><span class='pill p-create'>create</span></td><td><code>$(Enc $it.type)</code></td><td>$(Enc $it.address)</td></tr>") }
  [void]$sb.Append("</table></div>")
}

function Section($title, $rows, $pillClass, $pillText) {
  if ($rows.Count -eq 0) { return "<h2>$title</h2><p class='empty'>None.</p>" }
  $h = "<h2>$title</h2><table><tr><th>Action</th><th>Type</th><th>Address</th></tr>"
  foreach ($r in $rows) { $h += "<tr><td><span class='pill $pillClass'>$pillText</span></td><td><code>$(Enc $r.type)</code></td><td>$(Enc $r.address)</td></tr>" }
  return $h + "</table>"
}
[void]$sb.Append((Section "Changes (update / replace)" $update "p-update" "change"))
[void]$sb.Append((Section "Destroys" $delete "p-delete" "destroy"))

[void]$sb.Append(@"
<footer>Generated by scripts/tf_run_report.ps1 from a terraform plan. A plan makes no changes to your tenant.</footer>
</div></body></html>
"@)

Set-Content -Path $OutHtml -Value $sb.ToString() -Encoding UTF8
Write-Host "Run report written: $OutHtml ($($create.Count) to create, $($update.Count) to change, $($delete.Count) to destroy)"
