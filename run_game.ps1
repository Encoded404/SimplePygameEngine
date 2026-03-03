<#
PowerShell version of run_game.sh
Installs/updates requirements then copies a game into a temp folder and runs it.
#>

# Collect game folders that start with _ and strip leading underscore
$dirs = Get-ChildItem -Directory -Name -Path . | Where-Object { $_ -like '_*' }
$game_names = $dirs | ForEach-Object { $_.TrimStart('_') }

param(
    [int]$Index
)

if ($PSBoundParameters.ContainsKey('Index')) {
    if ($Index -lt 0 -or $Index -ge $game_names.Count) {
        Write-Error "Invalid game index: $Index"
        exit 1
    }
    $game_index = $Index
} else {
    for ($i = 0; $i -lt $game_names.Count; $i++) {
        Write-Host "$i`: $($game_names[$i])"
    }
    $response = Read-Host "Enter the number of the game to run"
    if (-not [int]::TryParse($response, [ref]$game_index)) {
        Write-Error "Invalid selection"
        exit 1
    }
}

if ($game_index -lt 0 -or $game_index -ge $game_names.Count) {
    Write-Error "Invalid game selection."
    exit 1
}

Write-Host "Running game: $($game_names[$game_index])"

# Install/update requirements
Write-Host "Installing/Updating requirements..."
python -m pip install --upgrade pip
if (Test-Path requirements.txt) {
    python -m pip install --upgrade -r requirements.txt
}

# Prepare temp folder
if (Test-Path temp) { Remove-Item -Recurse -Force temp }
New-Item -ItemType Directory -Path temp | Out-Null

# Copy selected game, engine and .venv
Copy-Item -Path ("_$($game_names[$game_index])\*") -Destination temp -Recurse -Force
if (Test-Path engine) { Copy-Item -Path engine -Destination temp -Recurse -Force }
if (Test-Path .venv) { Copy-Item -Path .venv -Destination temp -Recurse -Force }

Push-Location temp
try {
    python game.py
} finally {
    Pop-Location
    Remove-Item -Recurse -Force temp
}
