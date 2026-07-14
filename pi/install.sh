#!/bin/bash
# TESTATE Pi node installer. Run as root from a directory containing:
#   node.py buzzer.py avatar.py index.html (avatar.py/index.html from ../device)
#   config.json corpus.json (the node's identity -- not in the repo)
#   testate.service testate-heartbeat.service testate-heartbeat.timer
set -e

apt-get update -qq
apt-get install -y -qq --no-install-recommends avahi-daemon python3-gpiozero python3-lgpio

install -d /opt/testate
install -m 644 node.py buzzer.py avatar.py index.html /opt/testate/

install -d -o testate -g testate /var/lib/testate /var/lib/testate/backups
# never clobber a living corpus
[ -f /var/lib/testate/config.json ] || install -m 600 -o testate -g testate config.json /var/lib/testate/
[ -f /var/lib/testate/corpus.json ] || install -m 600 -o testate -g testate corpus.json /var/lib/testate/

install -m 644 testate.service testate-heartbeat.service testate-heartbeat.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now avahi-daemon testate.service testate-heartbeat.timer

sleep 2
systemctl --no-pager --lines=5 status testate.service
