#!/usr/bin/env bash
# Renders the home intro (blender/intro.py, both cuts) and the page titles (blender/title.py, one
# clip per word) headless, and encodes the web assets into public/intro/.
# BLENDER overrides the Blender executable. CUTS= (empty) skips the home intro, WORDS= the titles.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
blender="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
frames="$root/blender/frames"
out="$root/public/intro"
mkdir -p "$out"

# render_frames <script> <variable> <value>: renders that scene's frames into an emptied $frames,
# with the variable set for the script. Blender's output is shown and kept in $rendered.
render_frames() {
  rm -rf "$root/blender/frames"
  mkdir -p "$frames"
  # Blender wants a native path for its output template.
  local frames_native
  frames_native="$(cygpath -m "$frames" 2>/dev/null || echo "$frames")"
  rendered="$(env "$2=$3" "$blender" --background --python "$root/blender/$1" \
    --render-output "$frames_native/f_####" --render-format PNG --render-anim | tee /dev/stderr)"
}

# encode <name> <webm crf> <mp4 crf>: VP9 for most browsers, H.264 as the fallback. No audio track.
# bt709 tags keep Safari's video colours in step with the still images.
encode() {
  local color=(-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv)
  ffmpeg -y -loglevel error -framerate 30 -i "$frames/f_%04d.png" \
    -c:v libvpx-vp9 -b:v 0 -crf "$2" -row-mt 1 -pix_fmt yuv420p "${color[@]}" -an "$out/$1.webm"
  ffmpeg -y -loglevel error -framerate 30 -i "$frames/f_%04d.png" \
    -c:v libx264 -crf "$3" -preset slow -pix_fmt yuv420p "${color[@]}" -movflags +faststart -an "$out/$1.mp4"
}

# The page takes over from the video when the last cap lands. intro.py prints that time and
# src/main.ts holds it as FINALE: stop before encoding anything if the two differ.
check_finale() {
  local scene page
  scene="$(grep -o 'finale_seconds=[0-9.]*' <<<"$rendered" | head -n 1 | cut -d= -f2)"
  page="$(sed -n 's/^const FINALE = \([0-9.]*\)$/\1/p' "$root/src/main.ts")"
  if [ -z "$scene" ] || [ -z "$page" ] || ! awk -v a="$scene" -v b="$page" 'BEGIN { exit !(a + 0 == b + 0) }'; then
    echo "The finale times differ: blender/intro.py printed finale_seconds=${scene:-nothing}," \
      "and FINALE in src/main.ts is ${page:-not found}. Make them agree, then render again." >&2
    exit 1
  fi
}

# Home intro. Light compression: the scene is mostly dark gradients, which block up quickly.
for cut in ${CUTS-wide tall}; do
  render_frames intro.py INTRO_CUT "$cut"
  check_finale
  encode "intro-$cut" 24 19

  # First frame: shown while the video loads. Last frame: the hero background it fades into.
  first="$(ls "$frames" | sort | head -n 1)"
  last="$(ls "$frames" | sort | tail -n 1)"
  ffmpeg -y -loglevel error -i "$frames/$first" -c:v libwebp -quality 85 "$out/poster-$cut.webp"
  ffmpeg -y -loglevel error -i "$frames/$last" -c:v libwebp -quality 93 "$out/hero-$cut.webp"
done

# Page titles: one clip per word, and its last frame as the still shown without the video.
for word in ${WORDS-projects experience hobbies cooking gardening}; do
  render_frames title.py TITLE_WORD "$word"
  encode "title-$word" 34 24
  last="$(ls "$frames" | sort | tail -n 1)"
  ffmpeg -y -loglevel error -i "$frames/$last" -c:v libwebp -quality 82 "$out/title-$word.webp"
done

rm -rf "$root/blender/frames"
ls -l "$out"
