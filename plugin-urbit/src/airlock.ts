/**
 * Minimal Urbit Eyre airlock — the exact login + channel-poke sequence
 * proven against the live commons (see pi/urbit_probe.py, which posted
 * as ~tolwed-nimlun-fotsut-tintyn). No @urbit/http-api dependency: one
 * small class, lazy login, re-auth on 401/403.
 */

export interface UrbitConfig {
  url: string; // e.g. http://127.0.0.1:8086
  code: string; // ship +code
  ship: string; // patp WITHOUT leading ~, e.g. tolwed-nimlun-fotsut-tintyn
  commons: string; // channel nest, e.g. chat/~fotsut-tintyn/reflections
}

interface PokeAction {
  id: number;
  action: "poke";
  ship: string;
  app: string;
  mark: string;
  json: unknown;
}

export class Airlock {
  private cfg: UrbitConfig;
  private cookie: string | null = null;
  private channel: string | null = null;
  private id = 0;

  constructor(cfg: UrbitConfig) {
    this.cfg = cfg;
  }

  private async login(): Promise<void> {
    const res = await fetch(`${this.cfg.url}/~/login`, {
      method: "POST",
      body: `password=${this.cfg.code}`,
      redirect: "manual",
    });
    const setCookie = res.headers.get("set-cookie");
    if (!setCookie) throw new Error(`urbit login failed (${res.status})`);
    this.cookie = setCookie.split(";")[0];
    this.channel = `${this.cfg.url}/~/channel/eliza-${Date.now()}`;
  }

  private async put(actions: PokeAction[]): Promise<Response> {
    return fetch(this.channel as string, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Cookie: this.cookie as string,
      },
      body: JSON.stringify(actions),
    });
  }

  /** Poke an agent; re-login once on auth expiry. */
  async poke(app: string, mark: string, json: unknown): Promise<void> {
    if (!this.cookie) await this.login();
    this.id += 1;
    const action: PokeAction = {
      id: this.id,
      action: "poke",
      ship: this.cfg.ship,
      app,
      mark,
      json,
    };
    let res = await this.put([action]);
    if (res.status === 401 || res.status === 403) {
      await this.login();
      res = await this.put([action]);
    }
    if (!res.ok) throw new Error(`poke ${app}/${mark} -> ${res.status}`);
  }

  /** Post a chat message to the configured commons channel, as the ship. */
  async post(text: string): Promise<void> {
    const essay = {
      content: [{ inline: [text.slice(0, 1500)] }],
      sent: Date.now(),
      author: `~${this.cfg.ship}`,
      kind: "/chat",
      meta: null,
      blob: null,
    };
    await this.poke("channels", "channel-action-2", {
      channel: { nest: this.cfg.commons, action: { post: { add: essay } } },
    });
  }

  /** Join a group (idempotent on the ship side). */
  async joinGroup(flag: string): Promise<void> {
    await this.poke("groups", "group-join", { flag, "join-all": true });
  }
}
