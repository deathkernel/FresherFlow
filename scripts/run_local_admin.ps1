# Run FresherFlow locally with an explicitly configured admin account.
# Credentials are entered at runtime and are never written to source files.

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

# Prefer this repository's virtual environment so the hash generator and app
# use the same installed dependencies and Python interpreter.
$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Create/activate .venv and install requirements.txt."
    }
    $pythonExe = $pythonCommand.Source
}

$adminId = Read-Host "Admin ID (example: Admin@123)"
if ([string]::IsNullOrWhiteSpace($adminId)) {
    throw "Admin ID cannot be empty."
}

$securePassword = Read-Host "Admin password (input is hidden)" -AsSecureString
if ($securePassword.Length -eq 0) {
    throw "Admin password cannot be empty."
}

$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)

    # Use a temporary environment variable instead of PowerShell's native stdin
    # pipeline, which may encode strings as UTF-16LE on Windows PowerShell 5.1.
    $env:FRESHERFLOW_ADMIN_SETUP_PASSWORD = $plainPassword
    $passwordHash = & $pythonExe -c "import os; from werkzeug.security import generate_password_hash, check_password_hash; p=os.environ.pop('FRESHERFLOW_ADMIN_SETUP_PASSWORD'); h=generate_password_hash(p); assert check_password_hash(h, p); print(h)"
    Remove-Item Env:FRESHERFLOW_ADMIN_SETUP_PASSWORD -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($passwordHash -join ""))) {
        throw "Could not generate and verify the admin password hash. Run python -m pip install -r requirements.txt in .venv."
    }

    $env:ADMIN_EMAIL = $adminId.Trim().ToLowerInvariant()
    $env:ADMIN_PASSWORD_HASH = ($passwordHash -join "").Trim()
    $env:HOST = "127.0.0.1"

    Write-Host "Starting FresherFlow with the configured local admin account..."
    Write-Host "Python interpreter: $pythonExe"
    Write-Host "Admin login: http://127.0.0.1:5000/admin"
    & $pythonExe app.py
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainPassword = $null
    Remove-Item Env:FRESHERFLOW_ADMIN_SETUP_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_PASSWORD_HASH -ErrorAction SilentlyContinue
    Remove-Item Env:HOST -ErrorAction SilentlyContinue
}
