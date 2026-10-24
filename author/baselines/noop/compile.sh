#!/bin/sh
set -eu
mkdir -p /workspace/build
cc -O2 -o /workspace/build/dot /workspace/main.c
