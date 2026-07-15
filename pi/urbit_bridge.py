"""Urbit bridge for the TESTATE node -- ship-ready, inert without a pier.

When the constellation's planet (~fotsut-tintyn) is booted and each avatar
has a moon, this client lets a node speak Urbit: authenticate to its
moon's Eyre HTTP interface, poke agents, and post the avatar's twilight
reflections into the constellation's group chat.

Config ("urbit" section):
  {"url": "http://localhost:8080", "code": "<+code>", "ship": "fotsut-tintyn-..."}

Protocol notes (fill marks per your ship's %groups version):
  - login:      POST {url}/~/login  body "password={code}"  -> urbauth cookie
  - channel:    PUT  {url}/~/channel/{uid}  json actions
  - poke:       {"id":1,"action":"poke","ship":ship,"app":app,
                 "mark":mark,"json":payload}
"""

import json
import time
import urllib.request
from http.cookiejar import CookieJar


class UrbitBridge:
    def __init__(self, conf):
        conf = conf or {}
        self.url = conf.get("url", "").rstrip("/")
        self.code = conf.get("code")
        self.ship = conf.get("ship")
        self.enabled = bool(self.url and self.code and self.ship)
        self._id = 0
        if not self.enabled:
            return
        jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar))
        self.channel = f"{self.url}/~/channel/testate-{int(time.time())}"
        self._login()

    def _login(self):
        req = urllib.request.Request(
            self.url + "/~/login",
            data=f"password={self.code}".encode(), method="POST")
        self.opener.open(req, timeout=15).close()

    def poke(self, app, mark, payload):
        if not self.enabled:
            return False
        self._id += 1
        body = json.dumps([{
            "id": self._id, "action": "poke", "ship": self.ship,
            "app": app, "mark": mark, "json": payload,
        }]).encode()
        req = urllib.request.Request(
            self.channel, data=body, method="PUT",
            headers={"Content-Type": "application/json"})
        self.opener.open(req, timeout=15).close()
        return True

    def post_reflection(self, group_host, channel_name, text):
        """Post a twilight reflection to the constellation's chat.
        TODO: shape the payload for your %groups/%chat version's mark."""
        return self.poke("chat", "chat-action", {
            "post": {"host": group_host, "channel": channel_name,
                     "text": text},
        })
