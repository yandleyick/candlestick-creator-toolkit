[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Position = 0)][string]$Tool = 'list',
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$ToolArguments,
    [string]$ToolkitRoot = $env:TOOLKIT_ROOT
)
$ErrorActionPreference = 'Stop'
if (-not $ToolkitRoot) { $ToolkitRoot = 'D:\Tools\FMHy_Toolkit' }
$launcher = Join-Path $ToolkitRoot 'toolkit.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'Existing FMHY launcher not found. Set TOOLKIT_ROOT to the toolkit installation.'
}
& $launcher $Tool @ToolArguments
