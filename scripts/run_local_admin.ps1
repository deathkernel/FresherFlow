# Run FresherFlow locally with an explicitly configured admin account.
# Credentials are entered at runtime and are never written to source files.

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

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

    # Pass the password through a temporary process environment variable rather
    # than PowerShell's native-command stdin pipeline. Windows PowerShell 5.1
    # can encode piped strings as UTF-16LE, which can silently hash a different
    # password than the one entered in the browser.
    $env:FRESHERFLOW_ADMIN_SETUP_PASSWORD = $plainPassword
    $passwordHash = python -c "import os; from werkzeug.security import generate_password_hash; print(generate_password_hash(os.environ.pop('FRESHERFLOW_ADMIN_SETUP_PASSWORD')))"
    Remove-Item Env:FRESHERFLOW_ADMIN_SETUP_PASSWORD -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($passwordHash)) {
        throw "Could not generate the admin password hash. Activate the virtual environment and install requirements.txt first."
    }

    $env:ADMIN_EMAIL = $adminId.Trim().ToLowerInvariant()
    $env:ADMIN_PASSWORD_HASH = $passwordHash.Trim()

    Write-Host "Starting FresherFlow with the configured local admin account..."
    Write-Host "Admin login: http://127.0.0.1:5000/admin"
    python app.py
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainPassword = $null
    Remove-Item Env:FRESHERFLOW_ADMIN_SETUP_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_PASSWORD_HASH -ErrorAction SilentlyContinue
}
