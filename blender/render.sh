#!/usr/bin/env bash
# Renders both cuts of blender/intro.py headless and encodes the web assets into public/intro/.
# BLENDER overrides the Blender executable. CUTS= (empty) skips the home intro.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
blender="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
frames="$root/blender/frames"
out="$root/public/intro"
mkdir -p "$out"

for cut in ${CUTS-wide tall}; do
  rm -rf "$root/blender/frames"
  mkdir -p "$frames"

  # Blender wants a native path for its output template.
  frames_native="$(cygpath -m "$frames" 2>/dev/null || echo "$frames")"
  INTRO_CUT="$cut" "$blender" --background --python "$root/blender/intro.py" \
    --render-output "$frames_native/f_####" --render-format PNG --render-anim

  first="$(ls "$frames" | sort | head -n 1)"
  last="$(ls "$frames" | sort | tail -n 1)"

  # VP9 for most browsers, H.264 as the fallback. No audio track. Light compression: the scene is
  # mostly dark gradients, which block up quickly. bt709 tags keep Safari's
  # video colours in step with the still images.
  color=(-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv)
  ffmpeg -y -loglevel error -framerate 30 -i "$frames/f_%04d.png" \
    -c:v libvpx-vp9 -b:v 0 -crf 24 -row-mt 1 -pix_fmt yuv420p "${color[@]}" -an "$out/intro-$cut.webm"
  ffmpeg -y -loglevel error -framerate 30 -i "$frames/f_%04d.png" \
    -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p "${color[@]}" -movflags +faststart -an "$out/intro-$cut.mp4"

  # First frame: shown while the video loads. Last frame: the hero background it fades into.
  ffmpeg -y -loglevel error -i "$frames/$first" -c:v libwebp -quality 85 "$out/poster-$cut.webp"
  ffmpeg -y -loglevel error -i "$frames/$last" -c:v libwebp -quality 93 "$out/hero-$cut.webp"
done

# Page titles: one clip per word, and its last frame as the still shown without the video.
for word in ${WORDS-projects experience hobbies cooking gardening}; do
  rm -rf "$root/blender/frames"
  mkdir -p "$frames"
  frames_native="$(cygpath -m "$frames" 2>/dev/null || echo "$frames")"
  TITLE_WORD="$word" "$blender" --background --python "$root/blender/title.py"     --render-output "$frames_native/f_####" --render-format PNG --render-anim
  last="$(ls "$frames" | sort | tail -n 1)"
  color=(-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv)
  ffmpeg -y -loglevel error -framerate 30 -i "$frames/f_%04d.png"     -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p "${color[@]}" -an "$out/title-$word.webm"
  ffmpeg -y -loglevel error -framerate 30 -i "$frames/f_%04d.png"     -c:v libx264 -crf 24 -preset slow -pix_fmt yuv420p "${color[@]}" -movflags +faststart -an "$out/title-$word.mp4"
  ffmpeg -y -loglevel error -i "$frames/$last" -c:v libwebp -quality 82 "$out/title-$word.webp"
done

rm -rf "$root/blender/frames"
ls -l "$out"
