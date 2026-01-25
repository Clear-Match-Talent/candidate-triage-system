param(
  [Parameter(Mandatory=$true)]
  [string]$RunName,

  [Parameter(Mandatory=$true)]
  [string[]]$InputCsvs
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$runDir = Join-Path $repo ("runs\" + $RunName)
$inputDir = Join-Path $runDir "input"
$outputDir = Join-Path $runDir "output"

New-Item -ItemType Directory -Force -Path $inputDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Write-Host "Run dir: $runDir"

foreach ($csv in $InputCsvs) {
  Copy-Item -Force $csv $inputDir
}

Write-Host "1) Standardize + dedupe"
python -m ingestion.main (Join-Path $inputDir "*.csv") --output-dir $outputDir

Write-Host "2) Evaluate"
python evaluate_v3.py (Join-Path $outputDir "standardized_candidates.csv") (Join-Path $outputDir "evaluated.csv")

Write-Host "3) Bucket"
python tools/bucket_results.py (Join-Path $outputDir "evaluated.csv") --outdir $outputDir

Write-Host "Done. Outputs in $outputDir"
