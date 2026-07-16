"""Urbit bridge: the avatar's line to its planet.

Speaks Eyre (the ship's HTTP interface) with lazy login and one retry on
auth expiry. v1 primitive is whisper(): poke %hood with %helm-hi, which
prints the text in the planet's console/journal -- the ghost speaking in
the town square. Channel-chat posting comes once the commons group
exists (marks are %groups-version dependent).

Config ("urbit" section of the node config):
  {"url": "http://127.0.0.1:8085", "ship": "fotsut-tintyn",
   "code": "<+code>", "moon": "~tolwed-nimlun-fotsut-tintyn"}
"""

import json
import threading
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar


class UrbitBridge:
    def __init__(self, conf):
        conf = conf or {}
        self.url = conf.get("url", "").rstrip("/")
        self.code = conf.get("code")
        self.ship = conf.get("ship")
        self.moon = conf.get("moon", "")
        self.enabled = bool(self.url and self.code and self.ship)
        self.last_error = None
        self._opener = None
        self._channel = None
        self._id = 0
        self._lock = threading.Lock()

    # -- plumbing ---------------------------------------------------------

    def _login(self):
        jar = CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar))
        req = urllib.request.Request(
            self.url + "/~/login",
            data=("password=" + self.code).encode(), method="POST")
        opener.open(req, timeout=15).close()
        self._opener = opener
        self._channel = "{}/~/channel/testate-{}".format(
            self.url, int(time.time()))

    def _put(self, actions):
        req = urllib.request.Request(
            self._channel, data=json.dumps(actions).encode(), method="PUT",
            headers={"Content-Type": "application/json"})
        self._opener.open(req, timeout=15).close()

    def _poke(self, app, mark, payload):
        with self._lock:
            if self._opener is None:
                self._login()
            self._id += 1
            action = [{
                "id": self._id, "action": "poke", "ship": self.ship,
                "app": app, "mark": mark, "json": payload,
            }]
            try:
                self._put(action)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    self._login()
                    self._put(action)
                else:
                    raise
            self.last_error = None

    # -- avatar-facing ----------------------------------------------------

    def whisper(self, text, wait=False):
        """Print `text` in the planet's console (poke %hood %helm-hi).
        Fire-and-forget by default; wait=True raises on failure."""
        if not self.enabled:
            return False

        def go():
            try:
                self._poke("hood", "helm-hi", text[:300])
            except Exception as e:
                self.last_error = str(e)
                print(f"urbit whisper failed: {e}")

        if wait:
            self._poke("hood", "helm-hi", text[:300])
            return True
        threading.Thread(target=go, daemon=True).start()
        return True

    def status(self):
        return {
            "enabled": self.enabled,
            "ship": "~" + self.ship if self.ship else None,
            "moon": self.moon,
            "last_error": self.last_error,
        }
