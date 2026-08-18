# VoiSona Talk offline mock patch (same approach as VoiSona).
$ErrorActionPreference = 'Stop'
$src = 'C:\Users\abc\Desktop\dev\qaz123\voisona_dump\VoiSonaTalk.exe.orig'
$out = 'C:\Users\abc\Desktop\dev\qaz123\voisona_talk_test\VoiSona Talk.exe'
$newUrl = 'http://127.0.0.1:18080/api/v1'

New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
Copy-Item $src $out -Force
$b = [System.IO.File]::ReadAllBytes($out)

$pe = [BitConverter]::ToInt32($b, 0x3C)
$coff = $pe + 4
$numSections = [BitConverter]::ToUInt16($b, $coff + 2)
$sizeOfOptHdr = [BitConverter]::ToUInt16($b, $coff + 16)
$opt = $coff + 20
$secTable = $opt + $sizeOfOptHdr

$lastVA = 0; $lastVS = 0; $lastRawOff = 0; $lastRawSize = 0
for ($i=0; $i -lt $numSections; $i++) {
  $s = $secTable + $i*40
  $vs = [BitConverter]::ToUInt32($b, $s+8)
  $va = [BitConverter]::ToUInt32($b, $s+12)
  $rs = [BitConverter]::ToUInt32($b, $s+16)
  $ro = [BitConverter]::ToUInt32($b, $s+20)
  if ($va -gt $lastVA) { $lastVA=$va; $lastVS=$vs; $lastRawOff=$ro; $lastRawSize=$rs }
}
$secAlign = 0x1000; $fileAlign = 0x200
$newVA     = (($lastVA + $lastVS + $secAlign - 1) -band (-bnot ($secAlign-1)))
$newRawOff = (($b.Length + $fileAlign - 1) -band (-bnot ($fileAlign-1)))

$urlBytes = [System.Text.Encoding]::ASCII.GetBytes($newUrl) + @([byte]0x00)
$newVS = $urlBytes.Length
$newRawSize = (($newVS + $fileAlign - 1) -band (-bnot ($fileAlign-1)))

$hdr = New-Object byte[] 40
[System.Text.Encoding]::ASCII.GetBytes(".offline").CopyTo($hdr, 0)
[BitConverter]::GetBytes([UInt32]$newVS).CopyTo($hdr, 8)
[BitConverter]::GetBytes([UInt32]$newVA).CopyTo($hdr, 12)
[BitConverter]::GetBytes([UInt32]$newRawSize).CopyTo($hdr, 16)
[BitConverter]::GetBytes([UInt32]$newRawOff).CopyTo($hdr, 20)
$hdr[36]=0x40; $hdr[37]=0x00; $hdr[38]=0x00; $hdr[39]=0xC0

$hdrOff = $secTable + $numSections * 40
if ($hdrOff + 40 -gt 0x400) { throw "section table overflow" }
$newLen = $newRawOff + $newRawSize
$nb = New-Object byte[] $newLen
[Array]::Copy($b, 0, $nb, 0, $b.Length)
[Array]::Copy($hdr, 0, $nb, $hdrOff, 40)
[BitConverter]::GetBytes([UInt16]($numSections+1)).CopyTo($nb, $coff+2)
$newSizeOfImage = (($newVA + $newVS + $secAlign - 1) -band (-bnot ($secAlign-1)))
[BitConverter]::GetBytes([UInt32]$newSizeOfImage).CopyTo($nb, $opt+56)
[Array]::Copy($urlBytes, 0, $nb, $newRawOff, $urlBytes.Length)

# ---- patch base URL LEA -> new URL string ----
$leaVMA = 0x140008844
$leaFileOff = 0x400 + ($leaVMA - 0x140001000)
if ($nb[$leaFileOff] -ne 0x48 -or $nb[$leaFileOff+1] -ne 0x8D -or $nb[$leaFileOff+2] -ne 0x15) {
  throw "LEA bytes mismatch"
}
$target = [int64](0x140000000 + $newVA)
$next = [int64]$leaVMA + 7
$disp = [int64]$target - $next
[BitConverter]::GetBytes([uint32]($disp -band [int64]0xFFFFFFFF)).CopyTo($nb, $leaFileOff+3)

# ---- skip TS-Auth response-header checks (result code 8) ----
function FileOff([int64]$va) { 0x400 + ($va - 0x140001000) }
foreach ($va in @(0x140b9a75d, 0x140b9a77c, 0x140b978bb, 0x140b978db)) {
  $o = FileOff $va
  for ($i=0; $i -lt 6; $i++) { $nb[$o+$i] = 0x90 }
}

[System.IO.File]::WriteAllBytes($out, $nb)
"WROTE $out ($newLen bytes, sections=$($numSections+1))"
"newUrl VMA = 0x{0:X}" -f $target
"base URL LEA disp32 = 0x{0:X}" -f ($disp -band [int64]0xFFFFFFFF)
