package main

// Offline VoiSona launcher (replaces start_voisona_offline.ps1).
// Starts mock_server.exe (if not already running), then launches VoiSona.exe.
// All paths are resolved relative to this exe's own directory.

import (
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		return
	}
	dir := filepath.Dir(exe)

	// 1. start the mock server unless something is already listening on 18080
	conn, err := net.DialTimeout("tcp", "127.0.0.1:18080", 500*time.Millisecond)
	if err == nil {
		conn.Close()
	} else {
		mock := filepath.Join(dir, "mock_server.exe")
		if _, statErr := os.Stat(mock); statErr == nil {
			cmd := exec.Command(mock)
			cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
			_ = cmd.Start()
			time.Sleep(1500 * time.Millisecond)
		}
	}

	// 2. launch VoiSona.exe
	vsona := filepath.Join(dir, "VoiSona.exe")
	if _, statErr := os.Stat(vsona); statErr == nil {
		cmd := exec.Command(vsona)
		_ = cmd.Start()
	}
}
