# First Run Checklist (Headless CI)

## 1) Prepare a minimal local config

1. Copy config.local.example.json to config.local.json.
2. Fill one real Facebook group id.
3. Add a short test message.
4. Leave email/password empty if you will use cookies or secrets.

## 2) Build required secret value

Run in PowerShell:

```powershell
$json = Get-Content .\headless_ci_facebook\config.local.json -Raw
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
```

Create repo secret:

- FB_CONFIG_JSON_B64 (required)

## 3) Optional auth secrets

- FB_COOKIES_JSON_B64 (recommended if you already exported cookies)
- FB_EMAIL
- FB_PASSWORD

## 4) Trigger workflow manually

1. Open GitHub Actions.
2. Select workflow: facebook-headless-ci.
3. Click Run workflow.

## 5) Verify result

- If it fails, download artifact: headless-debug-artifacts.
- Inspect screenshot/html/txt to see if it was login/checkpoint/ui selector.
- Start with one group only, then scale.
