Param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

Write-Host "== Grok Story Handoff Windows build =="
Write-Host "Working directory: $(Get-Location)"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found in PATH. Install Python 3.10+ and enable 'Add Python to PATH'."
}

Write-Host "Python:"
python --version

Write-Host "Installing runtime requirements..."
python -m pip install -r requirements.txt

Write-Host "Installing PyInstaller..."
python -m pip install pyinstaller

$commonArgs = @(
    "--windowed",
    "--name", "GrokStoryHandoff",
    "--hidden-import", "grok_mhtml_bible_pipeline_v6",
    "--hidden-import", "grok_story_handoff_manager_v3_5_checkpoint_bible",
    "grok_handoff_gui.py"
)

if ($OneFile) {
    Write-Host "Building optional onefile executable..."
    python -m PyInstaller --onefile @commonArgs
    Write-Host "Build output: dist\GrokStoryHandoff.exe"
} else {
    Write-Host "Building recommended onedir executable..."
    python -m PyInstaller --onedir @commonArgs
    Write-Host "Build output: dist\GrokStoryHandoff\GrokStoryHandoff.exe"
}

Write-Host "Done."
