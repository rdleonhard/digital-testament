/**
 * Live proof: post to the commons through the Airlock class the plugin
 * uses. Run against a reachable ship (e.g. via `ssh -L 8086:127.0.0.1:8086`).
 *
 *   URBIT_URL=http://127.0.0.1:8086 URBIT_CODE=... URBIT_SHIP=... \
 *   URBIT_COMMONS=chat/~fotsut-tintyn/reflections \
 *   node --experimental-strip-types test/live-airlock.ts "message"
 */
import { Airlock } from "../src/airlock.ts";

const cfg = {
  url: process.env.URBIT_URL!,
  code: process.env.URBIT_CODE!,
  ship: process.env.URBIT_SHIP!.replace(/^~/, ""),
  commons: process.env.URBIT_COMMONS!,
};
const text = process.argv[2] ?? "airlock test from the ElizaOS plugin.";

const a = new Airlock(cfg);
await a.post(text);
console.log(`POSTED to ${cfg.commons} as ~${cfg.ship}`);
