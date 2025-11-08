<# 03_stage_review.ps1: copy N random clips into data\review #>
param(
  [int]$Count = 12,
  [string]$ClipsDir = "D:\videoLoraGenerationPipeline\data\clips",
  [string]$ReviewDir = "D:\videoLoraGenerationPipeline\data\review"
)
New-Item -ItemType Directory -Path $ReviewDir -Force | Out-Null
$clips = Get-ChildItem -Path $ClipsDir -Include *.mp4,*.mkv -File -Recurse
if (-not $clips) { Write-Host "No clips found." -ForegroundColor Yellow; exit 1 }
Get-Random -InputObject $clips -Count ([Math]::Min($Count, $clips.Count)) | ForEach-Object {
  Copy-Item $_.FullName -Destination (Join-Path $ReviewDir $_.Name) -Force
}
Write-Host "Staged $Count clips to $ReviewDir" -ForegroundColor Green
