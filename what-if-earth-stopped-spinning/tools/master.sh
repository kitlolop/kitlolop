#!/bin/bash
# build/mix_raw.wav (from audio.py) -> build/master_audio.wav
# two-pass EBU R128 loudnorm: -14 LUFS integrated, -1 dBTP, 48 kHz, exactly 60 s
set -e; cd "$(dirname "$0")/../build"
M=$(ffmpeg -hide_banner -i mix_raw.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
v() { echo "$M" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
ffmpeg -v error -y -i mix_raw.wav -af "loudnorm=I=-14:TP=-1:LRA=11:measured_I=$(v input_i):measured_TP=$(v input_tp):measured_LRA=$(v input_lra):measured_thresh=$(v input_thresh):offset=$(v target_offset):linear=true,aresample=48000" \
  -t 60 -c:a pcm_s24le master_audio.wav
ffmpeg -hide_banner -i master_audio.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tail -2
