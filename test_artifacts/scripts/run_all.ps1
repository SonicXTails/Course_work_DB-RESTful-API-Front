param(
  [string]$BaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://localhost:8000" }),
  [string]$AdminUser = "admin",
  [string]$AdminPass = "",
  [int]$Users = 10,
  [int]$SpawnRate = 5,
  [string]$Duration = "3m",
  [switch]$NoPostman,
  [switch]$NoLoad,
  [switch]$NoResilience
)

$ErrorActionPreference = "Stop"

# === Всегда работаем из корня test_artifacts, откуда лежат tests/postman/load ===
$scriptDir = $PSScriptRoot                       # ...\test_artifacts\scripts
$root = Split-Path $scriptDir -Parent            # ...\test_artifacts
Push-Location $root

Write-Host "==> API_BASE_URL: $BaseUrl"
$env:API_BASE_URL = $BaseUrl

# === Если токен уже есть — ничего не трогаем ===
if (-not $env:ADMIN_TOKEN) {
  try {
    # DRF authtoken
    $resp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api-token-auth/" -ContentType "application/json" -Body (@{username=$AdminUser;password=$AdminPass} | ConvertTo-Json)
    if ($resp.token) {
      $env:ADMIN_TOKEN = $resp.token
      if (-not $env:AUTH_SCHEME) { $env:AUTH_SCHEME = "Token" }
      Write-Host ">>> ADMIN token set (DRF Token)"
    } else { throw "No token" }
  } catch {
    try {
      # SimpleJWT
      $jwt = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/token/" -ContentType "application/json" -Body (@{username=$AdminUser;password=$AdminPass} | ConvertTo-Json)
      if ($jwt.access) {
        $env:ADMIN_TOKEN = $jwt.access
        if (-not $env:AUTH_SCHEME) { $env:AUTH_SCHEME = "Bearer" }
        Write-Host ">>> ADMIN token set (JWT Bearer)"
      } else { throw "No access token" }
    } catch {
      Write-Warning "Не удалось получить токен автоматически. Установи вручную: `$env:ADMIN_TOKEN и `$env:AUTH_SCHEME"
    }
  }
} else {
  Write-Host ">>> Использую уже заданный ADMIN_TOKEN ($($env:AUTH_SCHEME))"
}

# === Pytest ===
Write-Host "==> Running pytest"
if (-not (Test-Path ".\reports")) { New-Item -ItemType Directory -Path ".\reports" | Out-Null }
python -m pip install -q pytest requests pytest-cov | Out-Null
# подробный вывод, чтобы видеть причину, а не просто 'F'
python -m pytest -vv -rA

# === Postman ===
if (-not $NoPostman) {
  try {
    if (Get-Command newman -ErrorAction SilentlyContinue) {
      Write-Host "==> Running Postman (newman)"
      if (-not (Test-Path ".\reports")) { New-Item -ItemType Directory -Path ".\reports" | Out-Null }
      newman run .\postman\API_Car_Dealer.postman_collection.json -e .\postman\API_Car_Dealer.postman_environment.json --reporters cli,htmlextra --reporter-htmlextra-export .\reports\postman.html
    } else {
      Write-Warning "newman не установлен. Пропускаю Postman. Установи: npm i -g newman newman-reporter-htmlextra"
    }
  } catch { Write-Warning "Postman прогон завершился с ошибкой: $($_.Exception.Message)" }
}

# === Locust ===
if (-not $NoLoad) {
  Write-Host "==> Running Locust smoke (-u $Users -r $SpawnRate -t $Duration)"
  python -m pip install -q locust | Out-Null
  if (-not $env:LOAD_TOKEN) { $env:LOAD_TOKEN = $env:ADMIN_TOKEN }
  locust -f .\load\locustfile.py --host $BaseUrl --headless -u $Users -r $SpawnRate -t $Duration
}

# === Resilience (restore) ===
if (-not $NoResilience) {
  $restoreDir = Resolve-Path "..\restore" -ErrorAction SilentlyContinue
  if ($restoreDir) {
    Write-Host "==> Running resilience test (restore)"
    & .\resilience\resilience_test.ps1 -DbName "api_car" -Host "127.0.0.1" -Port 5432 -User "postgres"
  } else {
    Write-Warning "Папка restore не найдена рядом с test_artifacts. Пропускаю шаг восстановления."
  }
}

Pop-Location
Write-Host "==> Done."