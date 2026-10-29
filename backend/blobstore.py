"""File storage for uploads and rendered videos.

Default: files on local disk (path stored in files.path). With
SUPABASE_URL + SUPABASE_SERVICE_KEY set, bytes go to a private Supabase Storage
bucket and files.path holds "sb:<key>". Reads of remote files are served as a
redirect to a short-lived signed URL, so video seeking (Range requests) is
handled by Supabase, not this app. Transport is injectable for tests.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

REMOTE_PREFIX = "sb:"
SIGNED_URL_SECONDS = 3600


def _default_request(method, url, *, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


class LocalStore:
    remote = False

    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def put(self, name, data, mime):
        path = self.dir / name
        path.write_bytes(data)
        return str(path)

    def get(self, path):
        return Path(path).read_bytes()

    def exists(self, path):
        return Path(path).exists()

    def signed_url(self, path):
        return None


class SupabaseStore:
    remote = True

    def __init__(self, url, service_key, bucket="doppelai-files", request=_default_request):
        self.base = url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        self.key = service_key
        self.request = request

    def _headers(self, extra=None):
        h = {"Authorization": f"Bearer {self.key}", "apikey": self.key}
        h.update(extra or {})
        return h

    def put(self, name, data, mime):
        # POST /object/{bucket}/{path}; no upsert, so an existing key is never overwritten.
        status, _ = self.request("POST", f"{self.base}/object/{self.bucket}/{name}", data=data,
                                 headers=self._headers({"Content-Type": mime or "application/octet-stream"}))
        if status not in (200, 201):
            raise RuntimeError(f"storage upload failed: HTTP {status}")
        return REMOTE_PREFIX + name

    def _name(self, path):
        return path[len(REMOTE_PREFIX):]

    def get(self, path):
        status, body = self.request("GET", f"{self.base}/object/authenticated/{self.bucket}/{self._name(path)}",
                                    headers=self._headers())
        if status != 200:
            raise RuntimeError(f"storage download failed: HTTP {status}")
        return body

    def exists(self, path):
        try:
            self.signed_url(path)
            return True
        except Exception:
            return False

    def signed_url(self, path):
        status, body = self.request(
            "POST", f"{self.base}/object/sign/{self.bucket}/{self._name(path)}",
            data=json.dumps({"expiresIn": SIGNED_URL_SECONDS}).encode(),
            headers=self._headers({"Content-Type": "application/json"}))
        if status != 200:
            raise RuntimeError(f"storage sign failed: HTTP {status}")
        return self.base + json.loads(body)["signedURL"]


def make_store(local_dir, env):
    url, key = env.get("SUPABASE_URL", ""), env.get("SUPABASE_SERVICE_KEY", "")
    if url and key:
        return SupabaseStore(url, key, env.get("SUPABASE_BUCKET", "doppelai-files"))
    return LocalStore(local_dir)
