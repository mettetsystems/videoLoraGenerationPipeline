<# 
01_detect_and_cut.ps1
Batch scene detection & clip splitting using PySceneDetect + FFmpeg.

- Looks for .mp4/.mkv in data\sources
- Writes scene CSVs to data\scenedetect
- Writes clips to data\clips\<video_basename>\

Requirements:
- venv active with scenedetect installed
- ffmpeg in PATH
- configs\scenedetect.yaml present
#>
param(
  [string]$SourcesDir = "D:\videoLoraGenerationPipeline\data\sources",
  [string]$ScenesDir  = "D:\videoLoraGenerationPipeline\data\scenedetect",
  [string]$ClipsDir   = "D:\videoLoraGenerationPipeline\data\clips",
  [string]$ConfigYml  = "D:\videoLoraGenerationPipeline\configs\scenedetect.yaml"
)

New-Item -ItemType Directory -Path $ScenesDir -Force | Out-Null
New-Item -ItemType Directory -Path $ClipsDir  -Force | Out-Null

$cfg = Get-Content $ConfigYml -Raw
$threshold     = [regex]::Match($cfg, "threshold:\s*([0-9.]+)").Groups[1].Value
$min_scene_len = [regex]::Match($cfg, "min_scene_len:\s*([0-9]+)").Groups[1].Value

$videos = Get-ChildItem -Path $SourcesDir -Include *.mp4,*.mkv -File -Recurse
if (-not $videos) { Write-Host "No input videos in $SourcesDir" -ForegroundColor Yellow; exit 1 }

foreach ($vid in $videos) {
  Write-Host "`n=== Processing: $($vid.Name) ===" -ForegroundColor Cyan
  $base = [IO.Path]::GetFileNameWithoutExtension($vid.Name)
  $csv  = Join-Path $ScenesDir "$base-scenes.csv"
  $out  = Join-Path $ClipsDir  $base
  New-Item -ItemType Directory -Path $out -Force | Out-Null

  scenedetect -i $vid.FullName `
    detect-content --threshold $threshold --min-scene-len $min_scene_len `
    list-scenes --output $csv

  if ($LASTEXITCODE -ne 0) { Write-Host "Detect failed: $($vid.Name)" -ForegroundColor Red; continue }

  scenedetect -i $vid.FullName `
    detect-content --threshold $threshold --min-scene-len $min_scene_len `
    split-video -o $out

  if ($LASTEXITCODE -ne 0) { Write-Host "Split failed: $($vid.Name)" -ForegroundColor Red; continue }

  Write-Host "Done: CSV -> $csv ; Clips -> $out" -ForegroundColor Green
}
