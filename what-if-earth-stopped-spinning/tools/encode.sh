#!/bin/bash
# concat near-lossless chunks + mastered audio -> master (CRF 16) and release (CRF 20)
set -e; cd "$(dirname "$0")/../build"
printf "file 'chunk0a.mkv'\nfile 'chunk0b.mkv'\nfile 'chunk1.mkv'\nfile 'chunk2.mkv'\n" > frames/list.txt
for q in 16 20; do
  name=$([ $q = 16 ] && echo master || echo release); ab=$([ $q = 16 ] && echo 320k || echo 192k)
  ffmpeg -v error -y -f concat -safe 0 -i frames/list.txt -i master_audio.wav -map 0:v -map 1:a \
    -c:v libx264 -preset slow -crf $q -pix_fmt yuv420p -r 60 -profile:v high -tune animation \
    -c:a aac -b:a $ab -ar 48000 -t 60 -movflags +faststart \
    -metadata title="What if Earth stopped spinning" -metadata artist="kanren_g" ../what-if-earth-stopped-spinning_${name}.mp4
done
ls -la ../*.mp4
