# VoiSona offline mock patch: redirect API base URL -> local mock server
# (no code cave, no catalog redirect; app does its own real login against mock)
$ErrorActionPreference = 'Stop'
# build from the clean, unmodified original (not the installed exe, which may
# already carry other patches from earlier experiments)
$src = 'C:\Users\abc\Desktop\dev\qaz123\voisona_dump\VoiSona.exe.orig'
$out1 = 'C:\Users\abc\Desktop\dev\qaz123\voisona_dump\VoiSona.exe'
$out2 = 'C:\Users\abc\Desktop\dev\qaz123\voisona_test\VoiSona.exe'
$newUrl = 'http://127.0.0.1:18080/api/v1'

Copy-Item $src $out1 -Force
$b = [System.IO.File]::ReadAllBytes($out1)

$pe = [BitConverter]::ToInt32($b, 0x3C)
$coff = $pe + 4
$numSections = [BitConverter]::ToUInt16($b, $coff + 2)
$sizeOfOptHdr = [BitConverter]::ToUInt16($b, $coff + 16)
$opt = $coff + 20
$secTable = $opt + $sizeOfOptHdr

# find last section extent
$lastVA = 0; $lastVS = 0; $lastRawOff = 0; $lastRawSize = 0
for ($i=0; $i -lt $numSections; $i++) {
  $s = $secTable + $i*40
  $vs   = [BitConverter]::ToUInt32($b, $s+8)
  $va   = [BitConverter]::ToUInt32($b, $s+12)
  $rs   = [BitConverter]::ToUInt32($b, $s+16)
  $ro   = [BitConverter]::ToUInt32($b, $s+20)
  if ($va -gt $lastVA) { $lastVA=$va; $lastVS=$vs; $lastRawOff=$ro; $lastRawSize=$rs }
}
$secAlign = 0x1000; $fileAlign = 0x200
$newVA     = (($lastVA + $lastVS + $secAlign - 1) -band (-bnot ($secAlign-1)))
# place raw data after the END OF FILE (preserves Authenticode cert table at 0x146DE00)
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

# patch LEA at 0x1400634d4 (static init: lea rdx,[base_url]) -> point to new string
$leaVMA = 0x1400634d4
$leaFileOff = 0x400 + ($leaVMA - 0x140001000)
if ($nb[$leaFileOff] -ne 0x48 -or $nb[$leaFileOff+1] -ne 0x8D -or $nb[$leaFileOff+2] -ne 0x15) {
  throw "LEA bytes mismatch at 0x{0:X}" -f $leaFileOff
}
$target = [int64](0x140000000 + $newVA)
$next = [int64]$leaVMA + 7
$disp = [int64]$target - $next
[BitConverter]::GetBytes([uint32]($disp -band [int64]0xFFFFFFFF)).CopyTo($nb, $leaFileOff+3)

# restore FULL original is_logged_in body (p11 overwrote the whole 94-byte function
# with "B0 01 C3" + NOPs; restoring only 5 bytes left NOPs -> crash at 0xCCCC...)
$p11Off = 0x400 + (0x140A01A60 - 0x140001000)
$isLoggedInBytes = [byte[]](
  0x48,0x89,0x5c,0x24,0x08, 0x57, 0x48,0x83,0xec,0x20,
  0x48,0x8d,0xb9,0xf8,0x00,0x00,0x00, 0x48,0x8b,0xd9,
  0x48,0x8b,0xcf, 0xff,0x15,0xab,0x7a,0x4e,0x00,
  0x48,0x8b,0x83,0x98,0x00,0x00,0x00, 0x80,0x38,0x00, 0x74,0x1c,
  0x48,0x8b,0x83,0xa0,0x00,0x00,0x00, 0x80,0x38,0x00, 0x74,0x10,
  0x0f,0xb6,0x83,0xf0,0x00,0x00,0x00, 0x90, 0x84,0xc0, 0x74,0x04,
  0xb3,0x01, 0xeb,0x02, 0x32,0xdb, 0x48,0x8b,0xcf,
  0xff,0x15,0x30,0x7a,0x4e,0x00, 0x0f,0xb6,0xc3,
  0x48,0x8b,0x5c,0x24,0x30, 0x48,0x83,0xc4,0x20, 0x5f, 0xc3
)
[Array]::Copy($isLoggedInBytes, 0, $nb, $p11Off, $isLoggedInBytes.Length)

# ---- offline auth patches (skip server TS-Auth header verification) ----
function FileOff([int64]$va) { 0x400 + ($va - 0x140001000) }

# skip "TS-Auth" response-header check in login method 0x1409fbc50 (result code 8)
foreach ($va in @(0x1409fcdbd, 0x1409fcddc)) {
  $o = FileOff $va
  for ($i=0; $i -lt 6; $i++) { $nb[$o+$i] = 0x90 }
}
# skip "TS-Auth" response-header check in activate method 0x1409f91b0 (result code 8)
foreach ($va in @(0x1409f9f1b, 0x1409f9f3b)) {
  $o = FileOff $va
  for ($i=0; $i -lt 6; $i++) { $nb[$o+$i] = 0x90 }
}
# gate 0x140a01ad0: force catalog parser even if logged-in flag is 0
$g = FileOff 0x140a01b05
$nb[$g] = 0xEB
# login op 0x140a01d00: always return 0 (success) after the login methods run
$l = FileOff 0x140a01f31
$nb[$l] = 0x33; $nb[$l+1] = 0xC0; $nb[$l+2] = 0x90

[System.IO.File]::WriteAllBytes($out1, $nb)
Copy-Item $out1 $out2 -Force
"WROTE $out1 and $out2 ($newLen bytes, sections=$($numSections+1))"
"newUrl VMA = 0x{0:X}  string = $newUrl" -f $target
"LEA disp32 = 0x{0:X}" -f ($disp -band [int64]0xFFFFFFFF)
"p11 reverted to: {0}" -f (($nb[$p11Off..($p11Off+4)] | ForEach-Object { $_.ToString('X2') }) -join ' ')
