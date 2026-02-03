param(
  [Parameter(Position=0)]
  [string]$Command = "help",

  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)

# PowerShell doesn't execute from the current directory by default.
# This wrapper makes `./vision.ps1 build` feel natural.

$bat = Join-Path $PSScriptRoot "vision.bat"

if (-not (Test-Path $bat)) {
  throw "Missing: $bat"
}

& $bat $Command @Args
exit $LASTEXITCODE
