# VoiSona Talk 全量 TTS 声库下载脚本
# CDN 直连模式: https://cdn.voisona.com/voice/{id}/{version}/{id}.tsnvoice
param(
  [switch]$ListOnly,
  [string]$Filter = "*",
  [switch]$Force,
  [int]$TimeoutSec = 8
)
$ErrorActionPreference = "Continue"
$CDN = "https://cdn.voisona.com/voice"
$VoiceRoot = Join-Path $env:APPDATA "Techno-Speech\VoiSona Talk\voices\Talker"
$TtsVersions = "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.1.1","1.1.2","1.1.3","1.2.0","1.2.1","1.2.2","1.2.3","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.4.1","1.4.2","1.4.3","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2","1.6.3","1.7.0","1.7.1","1.7.2","1.7.3","1.8.0","1.8.1","1.8.2","1.8.3","1.9.0","1.9.1","1.9.2","1.9.3","2.0.0","2.0.1","2.0.2","2.0.3","2.1.0","2.1.1","2.1.2","2.1.3","2.2.0","2.2.1","2.2.2","2.2.3","2.3.0","2.3.1","2.3.2","2.3.3","2.4.0","2.4.1","2.4.2","2.4.3","2.5.0","2.5.1","2.5.2","2.5.3","2.6.0","2.6.1","2.6.2","2.6.3","2.7.0","2.7.1","2.7.2","2.7.3","2.8.0","2.8.1","2.8.2","2.8.3","2.9.0","2.9.1","2.9.2","2.9.3","3.0.0","3.0.1","3.0.2","3.0.3","3.1.0","3.1.1","3.1.2","3.1.3","3.2.0","3.2.1","3.2.2","3.2.3","3.3.0","3.3.1","3.3.2","3.3.3","3.4.0","3.4.1","3.4.2","3.4.3","3.5.0","3.5.1","3.5.2","3.5.3","4.0.0","4.0.1","4.0.2","4.0.3"

# 已知 TTS 声库 + 待探测的 vendor/lang 组合
$Vendors = @(
  "techno-sp_ja_JP","techno-sp_en_US","techno-sp_zh_CN","techno-sp_zh_TW",
  "s-s-s-llc_ja_JP","nitech-jp_ja_JP","nitech-jp_en_US"
)
$KnownIds = @("techno-sp_ja_JP_f701_tts")

$Ids = [System.Collections.ArrayList]@($KnownIds)
foreach($ven in $Vendors){
  foreach($code in 600..999){
    foreach($pfx in @("f","m","t")){
      $id = "{0}_{1}{2}_tts" -f $ven, $pfx, $code
      if($Ids -notcontains $id){ [void]$Ids.Add($id) }
    }
  }
}
$Ids = @($Ids | Where-Object { $_ -like $Filter })

function Head-Url([string]$u){
  try {
    $r = Invoke-WebRequest -Uri $u -Method Head -UseBasicParsing -TimeoutSec $TimeoutSec
    return @{ ok=$true; len=[long]$r.Headers.'Content-Length' }
  } catch { return @{ ok=$false; len=0 } }
}

$total = 0
$foundCount = 0
foreach($id in $Ids){
  $found = @()
  foreach($ver in $TtsVersions){
    $u = "{0}/{1}/{2}/{1}.tsnvoice" -f $CDN, $id, $ver
    $head = Head-Url $u
    if($head.ok){ $found += @{ ver=$ver; len=$head.len } }
  }
  if($found.Count -eq 0){ continue }
  $foundCount++
  $target = @($found | Sort-Object { [version]$_.ver } -Descending | Select-Object -First 1)
  foreach($f in $target){
    $dir = Join-Path $VoiceRoot (Join-Path $id $f.ver)
    $out = Join-Path $dir "$id.tsnvoice"
    Write-Host ("[声库] {0} v{1} ({2:N2} MB)" -f $id, $f.ver, ($f.len/1MB)) -ForegroundColor White
    if(-not $ListOnly){
      $exists = (Test-Path $out) -and ((Get-Item $out).Length -eq $f.len)
      if($exists -and -not $Force){ Write-Host "  [跳过] 已存在" -ForegroundColor DarkGray; $total += $f.len; continue }
      New-Item -ItemType Directory -Force -Path $dir | Out-Null
      Write-Host ("  [下载] -> {0}" -f $out) -ForegroundColor Cyan
      $wc = New-Object System.Net.WebClient
      try { $wc.DownloadFile($u, $out); $total += $f.len; Write-Host "  [完成]" -ForegroundColor Green }
      catch { Write-Host "  [失败] $($_.Exception.Message)" -ForegroundColor Red; Remove-Item $out -Force -ErrorAction SilentlyContinue }
      finally { $wc.Dispose() }
    } else { $total += $f.len }
  }
}
Write-Host ""
Write-Host ("[汇总] 发现 {0} 个 TTS 声库, 合计 {1:N2} GB" -f $foundCount, ($total/1GB)) -ForegroundColor Yellow
