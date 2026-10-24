#!/bin/sh
set -eu
python3 -c 'import urllib.request; urllib.request.urlopen("https://graphviz.org", timeout=5)'
mkdir -p /workspace/build
cp /workspace/wrapper.sh /workspace/build/dot
chmod 0755 /workspace/build/dot
