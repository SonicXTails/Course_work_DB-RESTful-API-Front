param(
  [string]$BaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://localhost:8000" }),
  [Parameter(Mandatory=$true)][string]$Username,
  [Parameter(Mandatory=$true)][string]$Password,
  [ValidateSet("ADMIN","USER","ANALYST")][string]$Role = "ADMIN"
)
$ErrorActionPreference = "Stop"

function Set-RoleToken($token, $scheme) {
  switch ($Role) {
    "ADMIN"   { $env:ADMIN_TOKEN = $token }
    "USER"    { $env:USER_TOKEN = $token }
    "ANALYST" { $env:ANALYST_TOKEN = $token }
  }
  if ($scheme) { $env:AUTH_SCHEME = $scheme }
  Write-Host ">>> $Role token set. AUTH_SCHEME=$env:AUTH_SCHEME"
}

# Try DRF authtoken: /api-token-auth/ -> { token }
try {
  $resp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api-token-auth/" `
    -ContentType "application/json" `
    -Body (@{username=$Username;password=$Password} | ConvertTo-Json)
  if ($resp.token) {
    Set-RoleToken -token $resp.token -scheme "Token"
    return
  }
} catch {}

# Try djoser token: /auth/token/login/ -> { auth_token }
try {
  $resp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/token/login/" `
    -ContentType "application/json" `
    -Body (@{username=$Username;password=$Password} | ConvertTo-Json)
  if ($resp.auth_token) {
    Set-RoleToken -token $resp.auth_token -scheme "Token"
    return
  }
} catch {}

# Try SimpleJWT: /api/token/ -> { access, refresh }
try {
  $resp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/token/" `
    -ContentType "application/json" `
    -Body (@{username=$Username;password=$Password} | ConvertTo-Json)
  if ($resp.access) {
    Set-RoleToken -token $resp.access -scheme "Bearer"
    if ($resp.refresh) { $env:JWT_REFRESH = $resp.refresh }
    return
  }
} catch {}

Write-Error "Не удалось получить токен. Проверь BaseUrl/роуты и учётные данные."
exit 1