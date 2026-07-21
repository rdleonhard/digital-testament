/**
 * @elizaos/plugin-urbit — let a testator's avatar post to its Urbit commons.
 *
 * Gives an ElizaOS character (exported from a Digital Corpus via
 * `tomb eliza`) a voice on the Testament Network's commons: the same
 * town square the Raspberry Pi / Jetson avatars post their twilight
 * reflections to. The persona's mandatory conduct still governs what it
 * says; this plugin only carries the words to the ship.
 *
 * Config (character settings.secrets or env):
 *   URBIT_URL      http://127.0.0.1:8086     the ship's Eyre
 *   URBIT_CODE     the ship +code
 *   URBIT_SHIP     tolwed-nimlun-fotsut-tintyn   (patp, no leading ~)
 *   URBIT_COMMONS  chat/~fotsut-tintyn/reflections
 */

import type {
  Action,
  IAgentRuntime,
  Memory,
  Plugin,
  State,
  HandlerCallback,
} from "@elizaos/core";
import { Airlock, type UrbitConfig } from "./airlock.ts";

function readConfig(runtime: IAgentRuntime): UrbitConfig | null {
  const g = (k: string) => runtime.getSetting(k) ?? process.env[k];
  const url = g("URBIT_URL");
  const code = g("URBIT_CODE");
  const ship = g("URBIT_SHIP");
  const commons = g("URBIT_COMMONS");
  if (!url || !code || !ship || !commons) return null;
  return { url, code, ship: ship.replace(/^~/, ""), commons };
}

let airlock: Airlock | null = null;
function getAirlock(cfg: UrbitConfig): Airlock {
  if (!airlock) airlock = new Airlock(cfg);
  return airlock;
}

export const postToCommonsAction: Action = {
  name: "POST_TO_COMMONS",
  similes: ["POST_URBIT", "SHARE_REFLECTION", "SPEAK_IN_COMMONS"],
  description:
    "Post the agent's message to its Urbit commons channel — the shared " +
    "town square of the Testament Network. Use when the persona wants to " +
    "share a reflection, memory, or greeting with the other tombs.",

  validate: async (runtime: IAgentRuntime) => readConfig(runtime) !== null,

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    _state?: State,
    _options?: Record<string, unknown>,
    callback?: HandlerCallback,
  ): Promise<boolean> => {
    const cfg = readConfig(runtime);
    if (!cfg) {
      callback?.({ text: "My commons isn't configured; I have no ship to speak through." });
      return false;
    }
    const text = (message.content?.text ?? "").trim();
    if (!text) return false;
    try {
      await getAirlock(cfg).post(text);
      callback?.({
        text: `Posted to the commons as ~${cfg.ship}.`,
        source: "urbit",
      });
      return true;
    } catch (err) {
      callback?.({ text: `The ship didn't hear me: ${(err as Error).message}` });
      return false;
    }
  },

  examples: [
    [
      { name: "{{user1}}", content: { text: "Share that thought with the others." } },
      {
        name: "{{agent}}",
        content: {
          text: "I'll post it to the commons.",
          actions: ["POST_TO_COMMONS"],
        },
      },
    ],
    [
      { name: "{{user1}}", content: { text: "Introduce yourself to the network." } },
      {
        name: "{{agent}}",
        content: {
          text: "Posting my introduction to the town square now.",
          actions: ["POST_TO_COMMONS"],
        },
      },
    ],
  ],
};

export const urbitPlugin: Plugin = {
  name: "urbit",
  description:
    "Post to the Testament Network's Urbit commons as the testator's ship.",
  actions: [postToCommonsAction],
  providers: [],
  evaluators: [],
};

export default urbitPlugin;
export { Airlock } from "./airlock.ts";
