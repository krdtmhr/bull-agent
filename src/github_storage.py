import base64
import json
import urllib.request
import urllib.error


class GithubStorage:
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo
        self._base = "https://api.github.com"

    def _headers(self) -> dict:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "bull43-agent/1.0",
            "Content-Type": "application/json",
        }

    def read(self, path: str) -> tuple:
        """Returns (data_dict, sha) or ({}, None) if not found."""
        url = f"{self._base}/repos/{self.repo}/contents/{path}"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                meta = json.loads(resp.read())
            content = base64.b64decode(meta["content"]).decode("utf-8")
            return json.loads(content), meta["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}, None
            raise

    def write(self, path: str, data, sha, message: str = "update state") -> None:
        """Write JSON to GitHub repo. sha=None creates a new file."""
        url = f"{self._base}/repos/{self.repo}/contents/{path}"
        content = base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")
        payload = {"message": message, "content": content}
        if sha:
            payload["sha"] = sha
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
