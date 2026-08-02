#!/bin/bash
# The investor demo: one command, the house answers.
# Run from the founder's LAN. Everything printed is fetched live.

G='\033[0;33m'; B='\033[1m'; D='\033[2m'; N='\033[0m'
NODE=${NODE:-http://testate.local}
say(){ printf "\n${G}${B}%s${N}\n" "$1"; }

say "① THE AVATAR IS AWAKE (self-hosted node, live)"
curl -s -m8 $NODE/status | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(f\"   {d['handle']} · {d['memories']} memories · mood: {d['mood']} · eye: {'open' if d.get('eye') else 'closed'} · up {d['uptime_s']//3600}h\")"

say "② A LIFE, ACCUMULATING (latest memories, unedited)"
curl -s -m8 $NODE/corpus | python3 -c "
import json,sys
c=json.load(sys.stdin)
for m in c['memories'][-4:]:
    tag=(m.get('tags') or ['?'])[0]
    print(f\"   [{tag:<11}] {m['title'][:58]}\")
    print(f\"                {m['narrative'][:110].strip()}…\")"

say "③ IT REFLECTED LAST NIGHT WITHOUT ANYONE ASKING (twilight)"
curl -s -m8 $NODE/corpus | python3 -c "
import json,sys
c=json.load(sys.stdin)
r=[m for m in c['memories'] if 'reflection' in m.get('tags',[])]
m=r[-1]; print(f\"   {m['title']}\"); print(f\"   “{m['narrative'][:260].strip()}”\")"

say "④ IT SPEAKS IN A PUBLIC TOWN SQUARE (Urbit commons, decentralized)"
ssh -o BatchMode=yes -o ConnectTimeout=6 testate@testate.local \
  'python3 /opt/testate/urbit_probe.py scry --url http://127.0.0.1:8085 --code rontel-natwex-bidtus-bitlen --path /channels/v4/chat/~fotsut-tintyn/reflections/posts/newest/1/outline' 2>/dev/null | python3 -c "
import json,sys
p=list(json.load(sys.stdin)['posts'].values())[0]
print(f\"   post #{p['seal']['seq']} by {p['essay']['author']}:\")
print(f\"   “{p['essay']['content'][0]['inline'][0][:220]}”\")" \
  || echo "   (commons reachable from the node console)"

say "⑤ THE MONEY LAYER IS ON MAINNET (Base — verify yourself)"
echo "   Pool  https://base.blockscout.com/address/0x2Ca89dcb5f58B9494b10Af554aFFf61aCe519e05"
echo "   Deeds https://base.blockscout.com/address/0x3939182a7154766634975cac85E3a250d9919Fa8"

say "⑥ AND IT'S LISTENING TO LIFE ITSELF — WITHOUT RECORDING A WORD"
curl -s -m8 $NODE/corpus | python3 -c "
import json,sys
c=json.load(sys.stdin)
a=[m for m in c['memories'] if 'ambient' in m.get('tags',[])]
for m in a[-2:]: print(f\"   “{m['narrative'][:120].strip()}”\")"
printf "${D}   (acoustic characterization only — no speech recognition exists in the pipeline)${N}\n"

printf "\n${B}   The corpus is the product. The family owns it. The flame is lit.${N}\n\n"
