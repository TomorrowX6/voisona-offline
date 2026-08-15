#!/usr/bin/env python3
"""VoiSona offline login mock server.

Serves the embedded TSSinger catalog as the /auth/token/ response, with all
42 voices moved into the "licenses" array (so the app shows them as purchased).
Echoes the request's "email" back in the JWT so any account/password is accepted.
Binds 127.0.0.1:18080 by default.
"""
import json, os, time, base64, hmac, hashlib, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def b64url(data):
    if isinstance(data, (dict, list)):
        data = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(payload, secret="voisona-offline"):
    h = b64url({"alg": "HS256", "typ": "JWT"})
    p = b64url(payload)
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"


HOST = "127.0.0.1"
PORT = int(os.environ.get("VOISONA_MOCK_PORT", "18080"))
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_info_tssinger.json")


def load_catalog():
    with open(JSON_PATH, "rb") as f:
        raw = f.read()
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
    data = json.loads(raw.decode("utf-8"))
    ui = data["user_info"]
    if os.environ.get("VOISONA_MOCK_MERGE", "1") != "0":
        owned = ui.get("licenses", [])
        trial = ui.get("trial_licenses", [])
        ui["licenses"] = owned + trial
        ui["trial_licenses"] = []
    return data


CATALOG = load_catalog()
print(f"[mock] loaded {len(CATALOG['user_info']['licenses'])} owned voices "
      f"(licenses+trials merged) from {JSON_PATH}", flush=True)


def build_response(email):
    """Build a fresh token response, echoing the caller's email."""
    data = json.loads(json.dumps(CATALOG))  # deep copy
    now = int(time.time())
    email = email or "user@local"
    # match the real server's token lifetimes: access ~5min, refresh ~24h
    data["access"] = make_jwt({"token_type": "access", "exp": now + 300,
                               "iat": now, "jti": str(uuid.uuid4()), "email": email})
    data["refresh"] = make_jwt({"token_type": "refresh", "exp": now + 86400,
                                "iat": now, "jti": str(uuid.uuid4()), "email": email})
    return data


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # match WinInet (the app uses JUCE->WinInet)

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # mimic the real server's response headers (the token header may be required)
        self.send_header("RESPONSE_HEADER_NAME", str(uuid.uuid4()).replace("-", ""))
        self.send_header("Allow", "POST, OPTIONS")
        self.send_header("Content-Language", "ja")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Vary", "Accept-Language, Cookie, origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Server", "nginx/1.30.0")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n) if n else b""
        email = ""
        try:
            email = json.loads(body.decode("utf-8")).get("email", "")
        except Exception:
            pass
        print(f"[mock] {time.strftime('%H:%M:%S')} POST {self.path} email={email} "
              f"body={body.decode('utf-8', 'replace')[:400]}", flush=True)
        if "/auth/token/" in self.path and "verify" not in self.path:
            # login: return the full 42-voice catalog (trials merged into licenses)
            vpath = os.environ.get("VOISONA_MOCK_VERBATIM")
            if vpath and os.path.exists(vpath):
                with open(vpath, "rb") as f:
                    raw = f.read()
                if raw[:3] == b"\xef\xbb\xbf":
                    raw = raw[3:]
                self._send(200, raw.decode("utf-8", "replace"))
            else:
                self._send(200, build_response(email))
        else:
            # /auth/token/verify/  /auth/activate/  /auth/activate/voice/
            # empty JSON object (no "code" key) = success in the app's parser
            self._send(200, {})

    def do_GET(self):
        print(f"[mock] {time.strftime('%H:%M:%S')} GET {self.path}", flush=True)
        if "news" in self.path:
            self._send(200, [])
        else:
            self._send(200, {})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[mock] listening on http://{HOST}:{PORT}/", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
