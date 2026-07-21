"""Command line for the Digital Executor.

    tomb convert 25000              plan a USD -> VVV -> Diem endowment
    tomb provision --owner "..."    issue/record the estate inference key
    tomb build corpus.json          validate corpus, emit persona prompt
    tomb eliza corpus.json          export an ElizaOS character file
    tomb chat corpus.json           converse with the Digital Persona
    tomb heartbeat                  minimal ping to stay an active staker
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__, chat, convert, eliza, persona, provision


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="tomb", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="plan USD -> VVV -> Diem endowment")
    c.add_argument("usd", type=float, help="endowment amount in USD")
    c.add_argument("--vvv-price", type=float, default=None,
                   help="VVV/USD (default: fetch live from CoinGecko)")
    c.add_argument("--total-staked", type=float,
                   default=convert.DEFAULT_TOTAL_ACTIVE_STAKED_VVV,
                   help="total ACTIVE staked VVV network-wide")
    c.add_argument("--capacity", type=float,
                   default=convert.DEFAULT_NETWORK_CAPACITY_DIEM,
                   help="network daily capacity in Diem")
    c.add_argument("--usd-per-diem", type=float,
                   default=convert.DEFAULT_USD_PER_DIEM,
                   help="planning value of 1 Diem in USD of inference")

    pr = sub.add_parser("provision", help="issue/record the estate API key")
    pr.add_argument("--owner", required=True,
                    help='e.g. "Estate of Arthur R. Vale, Digital Persona Trust"')
    pr.add_argument("--store-dir", default=".",
                    help="where estate_keys.json lives (default: cwd)")

    b = sub.add_parser("build", help="validate corpus and emit persona prompt")
    b.add_argument("corpus", help="path to corpus JSON")
    b.add_argument("-o", "--out", default=None,
                   help="write prompt to file instead of stdout")

    el = sub.add_parser("eliza", help="export an ElizaOS character file")
    el.add_argument("corpus", help="path to corpus JSON")
    el.add_argument("-o", "--out", default=None,
                    help="write character JSON to file instead of stdout")

    ch = sub.add_parser("chat", help="converse with the Digital Persona")
    ch.add_argument("corpus", help="path to corpus JSON")
    ch.add_argument("--model", default=chat.DEFAULT_MODEL)

    hb = sub.add_parser("heartbeat",
                        help="1-token ping so the stake stays 'active'")
    hb.add_argument("--model", default=chat.DEFAULT_MODEL)

    args = p.parse_args(argv)

    if args.cmd == "convert":
        price = args.vvv_price
        if price is None:
            try:
                price = convert.fetch_vvv_price_usd()
            except Exception as e:
                print(f"Could not fetch live VVV price ({e}); "
                      "pass --vvv-price explicitly.", file=sys.stderr)
                return 1
        plan = convert.plan_endowment(
            args.usd, price,
            total_active_staked_vvv=args.total_staked,
            network_capacity_diem=args.capacity,
            usd_per_diem=args.usd_per_diem,
        )
        print(plan.summary())

    elif args.cmd == "provision":
        record = provision.provision(args.owner, store_dir=args.store_dir)
        print(f"Key record for {record['owner']}: {record['status']}")
        if record.get("api_key"):
            print("Inference key issued and stored in estate_keys.json "
                  "(mode 600). Guard it like a bearer asset.")
        if record.get("note"):
            print(record["note"])

    elif args.cmd == "build":
        corpus = persona.load_corpus(args.corpus)
        prompt = persona.build_system_prompt(corpus)
        if args.out:
            Path(args.out).write_text(prompt + "\n")
            print(f"Persona prompt written to {args.out} "
                  f"({len(prompt):,} chars)")
        else:
            print(prompt)

    elif args.cmd == "eliza":
        character = eliza.export(args.corpus)
        text = json.dumps(character, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text + "\n")
            print(f"ElizaOS character written to {args.out} "
                  f"({character['name']}, {len(character['lore'])} lore, "
                  f"{len(character['knowledge'])} knowledge entries)")
        else:
            print(text)

    elif args.cmd == "chat":
        corpus = persona.load_corpus(args.corpus)
        chat.repl(persona.build_system_prompt(corpus), model=args.model)

    elif args.cmd == "heartbeat":
        chat.heartbeat(model=args.model)
        print("Heartbeat sent; stake remains in the active set.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
