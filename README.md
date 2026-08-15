# VoiSona 离线补丁 (Offline Patch)

让 VoiSona `v1.18.0.5` 在**无网络、无 Host 目录**的情况下离线运行：登录窗口/`config.json` 填写**任意账号密码**即可，42 个 TSSinger 声库全部显示为「已购买」并可正常选用。

> 仅用于研究/备份个人已购声库。请遵守 Techno-Speech 的服务条款。

## 原理

VoiSona 的登录/激活请求走 `/api/v1/` 接口，并在解析响应时校验服务器返回的 `TS-Auth` 响应头。本方案：

1. 把 exe 内置的 API base URL 重定向到本机 `127.0.0.1:18080` 的 mock 服务器（新增一个 `.offline` 区段存放 URL）。
2. 二进制 patch 掉登录 / 激活两处的 `TS-Auth` 校验跳转，让流程直接解析响应体。
3. mock 服务器返回内嵌的 42 声库目录（trial 已合并进 licenses），并回显请求邮箱签发 JWT，所以任意账号密码都通过。

## 文件结构

```
├── apply_mock_patch.ps1        # 一键给 VoiSona.exe 打补丁（从干净原版生成）
├── deploy_offline.ps1          # 部署到 C:\Program Files（需管理员）
├── go_offline/
│   ├── mock/                   # 本地 mock API 服务器（Go）
│   │   ├── main.go
│   │   ├── go.mod
│   │   └── user_info_merged.json   # 内嵌的 42 声库目录（已脱敏）
│   └── launcher/               # 启动器（Go）：先起 mock，再起 VoiSona
│       ├── main.go
│       └── go.mod
└── legacy/                     # 早期 Python/PowerShell 版本（参考）
    ├── mock_server.py
    └── start_voisona_offline.ps1
```

## 构建（Go ≥ 1.26）

```powershell
cd go_offline\mock
go build -buildvcs=false -ldflags "-s -w" -o mock_server.exe .
cd ..\launcher
go build -buildvcs=false -ldflags "-s -w -H windowsgui" -o VoiSona_offline.exe .
```

## 使用

1. 用 `apply_mock_patch.ps1` 生成补丁后的 `VoiSona.exe`（它会从 `voisona_dump\VoiSona.exe.orig` 读取干净原版）。
2. 把以下三个文件放到 VoiSona 安装目录（同目录）：
   - `VoiSona.exe`（补丁后）
   - `mock_server.exe`
   - `VoiSona_offline.exe`
3. 双击 `VoiSona_offline.exe`（会先启动 mock 再启动 VoiSona，全部相对路径）。
4. 登录时填**任意邮箱 + 任意密码**即可。

## 补丁明细（VMA → 修改）

| 位置 | 修改 | 作用 |
|------|------|------|
| `0x1400634D4` | base URL LEA → 新 `.offline` 区段 URL | 重定向到 `http://127.0.0.1:18080/api/v1` |
| `0x1409FCDBD` / `0x1409FCDDC` | `je` → NOP | 跳过登录响应的 `TS-Auth` 校验 |
| `0x1409F9F1B` / `0x1409F9F3B` | `je` → NOP | 跳过激活响应的 `TS-Auth` 校验 |
| `0x140A01B05` | `jne` → `jmp` | gate 始终调用声库解析器 |
| `0x140A01F31` | `mov rax,rdi` → `xor eax,eax` | 登录操作始终返回成功 |

## 免责声明

本仓库仅包含补丁脚本、Go 源码与**脱敏后的**声库目录（账号 UUID 已置零、订阅号已清空）。不包含 VoiSona 原始二进制、账号凭据或真实 token。
