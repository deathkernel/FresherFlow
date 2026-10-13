# Local admin setup (Windows PowerShell)

The repository intentionally does not ship a default administrator account. From the project root, activate the virtual environment and install the project requirements first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the application with the interactive helper:

```powershell
.\scripts\run_local_admin.ps1
```

Enter the admin ID and password when prompted. The password prompt is hidden. The helper creates a Werkzeug password hash in memory, exposes the credentials only to that server process, and clears the environment variables when the server exits. It does not write the password or hash to the repository.

Open `http://127.0.0.1:5000/admin`. If repeated incorrect attempts triggered the login throttle, wait for the short lockout to expire before trying again. The configured admin ID is normalized to lowercase; the password is case-sensitive.

If the helper cannot run `python`, repair/recreate the virtual environment using an installed Python 3.11+ interpreter, then reinstall `requirements.txt`.
