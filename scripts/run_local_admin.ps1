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
    $passwordHash = $plainPassword | python -c "import sys; from werkzeug.security import generate_password_hash; print(generate_password_hash(sys.stdin.readline().rstrip('\r\n')))"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($passwordHash)) {
        throw "Could not generate the admin password hash. Install the requirements first."
    }

    $env:ADMIN_EMAIL = $adminId.Trim().ToLowerInvariant()
    $env:ADMIN_PASSWORD_HASH = $passwordHash.Trim()
    python app.py
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainPassword = $null
    Remove-Item Env:ADMIN_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:ADMIN_PASSWORD_HASH -ErrorAction SilentlyContinue
}
