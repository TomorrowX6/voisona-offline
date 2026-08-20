package main

// Offline mock API server for VoiSona (replaces mock_server.py).
// Serves the embedded 42-voice TSSinger catalog as the /auth/token/ response,
// with all trials already merged into the "licenses" array so the app shows
// them as purchased. Echoes the request email into a freshly-signed JWT so any
// account/password is accepted. Binds 127.0.0.1:18080.

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	_ "embed"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

//go:embed user_info_merged.json
var mergedUserInfo []byte // pre-merged TSSinger user_info (42 licenses, 0 trials)

//go:embed user_info_talker_merged.json
var mergedTalkerUserInfo []byte // pre-merged TSTalker user_info (1 license)

func b64url(b []byte) string {
	return base64.RawURLEncoding.EncodeToString(b)
}

func randomHex(n int) string {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		return "0000000000000000"
	}
	return hex.EncodeToString(b)
}

// makeJWT builds an HS256 JWT with the given payload.
func makeJWT(secret string, payload map[string]interface{}) string {
	h := b64url([]byte(`{"alg":"HS256","typ":"JWT"}`))
	p, _ := json.Marshal(payload)
	pp := b64url(p)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(h + "." + pp))
	return h + "." + pp + "." + b64url(mac.Sum(nil))
}

// jwtEmail extracts the "email" claim from a JWT payload (signature not checked).
func jwtEmail(t string) string {
	parts := strings.Split(t, ".")
	if len(parts) != 3 {
		return ""
	}
	p, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return ""
	}
	var payload map[string]interface{}
	if json.Unmarshal(p, &payload) != nil {
		return ""
	}
	if e, ok := payload["email"].(string); ok {
		return e
	}
	return ""
}

func send(w http.ResponseWriter, body []byte) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Content-Length", strconv.Itoa(len(body)))
	w.Header().Set("Content-Language", "ja")
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Server", "nginx/1.30.0")
	w.WriteHeader(http.StatusOK)
	w.Write(body)
}

func handler(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	switch {
	case r.Method == "GET" && strings.Contains(path, "news"):
		log.Printf("[mock] GET %s -> []", path)
		send(w, []byte("[]"))
	case r.Method == "POST" && strings.Contains(path, "/auth/token/"):
		// login and verify both return the catalog with fresh tokens.
		// login sends {"email":...}; verify sends {"token":"<jwt>"} whose
		// payload carries the email.
		body, _ := io.ReadAll(r.Body)
		var req map[string]interface{}
		json.Unmarshal(body, &req)
		email := ""
		if e, ok := req["email"].(string); ok {
			email = e
		} else if t, ok := req["token"].(string); ok {
			email = jwtEmail(t)
		}
		// choose catalog by product type (TSSinger vs TSTalker)
		ui := mergedUserInfo
		if ty, ok := req["type"].(string); ok && ty == "TSTalker" {
			ui = mergedTalkerUserInfo
		}
		now := time.Now().Unix()
		access := makeJWT("voisona-offline", map[string]interface{}{
			"token_type": "access", "exp": now + 300, "iat": now,
			"jti": randomHex(16), "email": email,
		})
		refresh := makeJWT("voisona-offline", map[string]interface{}{
			"token_type": "refresh", "exp": now + 86400, "iat": now,
			"jti": randomHex(16), "email": email,
		})
		resp := []byte(`{"refresh":"` + refresh + `","access":"` + access +
			`","user_info":` + string(ui) + `}`)
		log.Printf("[mock] POST %s email=%s body=%s", path, email, string(body))
		send(w, resp)
	default:
		// /auth/activate/  /auth/activate/voice/  /editors/...
		// -> empty JSON object (no "code" key = success)
		log.Printf("[mock] %s %s -> {}", r.Method, path)
		send(w, []byte("{}"))
	}
}

func main() {
	// log to the console only (no log file next to the exe)
	log.SetOutput(os.Stdout)
	log.SetFlags(log.Ltime) // "15:04:05" prefix, like the python mock
	addr := "127.0.0.1:18080"
	http.HandleFunc("/", handler)
	log.Printf("[mock] listening on http://%s/", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("[mock] %v", err)
	}
}
