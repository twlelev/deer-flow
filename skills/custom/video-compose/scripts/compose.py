#!/usr/bin/env python3
"""
Video Compose Script
Merges video clips and audio tracks into a final composed MP4 using MoviePy.
"""

import argparse
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compose video clips with audio into a final MP4."
    )
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="One or more video file paths (space-separated).",
    )
    parser.add_argument(
        "--audio",
        default=None,
        help="Audio file path to use as the final audio track.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output video file path (e.g. /mnt/user-data/outputs/final.mp4).",
    )
    parser.add_argument(
        "--match-audio-duration",
        action="store_true",
        default=False,
        help="Stretch or trim video clips to match total audio duration.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=25,
        help="Output frames per second (default: 25).",
    )
    parser.add_argument(
        "--quality",
        choices=["low", "medium", "high"],
        default="medium",
        help="Output quality preset: low / medium / high (default: medium).",
    )
    return parser.parse_args()


# Map quality presets to ffmpeg bitrate strings
QUALITY_BITRATE = {
    "low": "500k",
    "medium": "2000k",
    "high": "5000k",
}


def load_clips(video_paths):
    """Load and return a list of VideoFileClip objects."""
    from moviepy.editor import VideoFileClip

    clips = []
    for path in video_paths:
        if not os.path.isfile(path):
            print(f"Error: video file not found: {path}", file=sys.stderr)
            sys.exit(1)
        clips.append(VideoFileClip(path))
    return clips


def match_duration(concatenated_clip, audio_duration):
    """
    Adjust the concatenated video clip to match the given audio duration.

    - If video is shorter than audio: loop/repeat the last frame by
      speeding nothing — instead we loop the whole clip using fx.
    - If video is longer than audio: trim to audio duration.
    - If video is shorter: speed-down the whole clip (slow it down) to fill.
    """
    from moviepy.editor import concatenate_videoclips

    video_duration = concatenated_clip.duration

    if abs(video_duration - audio_duration) < 0.05:
        # Close enough, no adjustment needed
        return concatenated_clip

    # Calculate the speed factor needed so that video fills audio duration
    speed_factor = video_duration / audio_duration

    if speed_factor == 1.0:
        return concatenated_clip

    # Apply speed change: speed_factor > 1 speeds up (video was longer than audio),
    # speed_factor < 1 slows down (video was shorter than audio).
    adjusted = concatenated_clip.fx(
        __import__("moviepy.video.fx.speedx", fromlist=["speedx"]).speedx,
        speed_factor,
    )
    # After speed change the duration should now equal audio_duration.
    # Trim to exact duration in case of floating-point rounding.
    adjusted = adjusted.subclip(0, min(audio_duration, adjusted.duration))
    return adjusted


def compose(args):
    try:
        from moviepy.editor import (
            AudioFileClip,
            concatenate_videoclips,
        )
        import moviepy.video.fx.speedx as vfx_speedx
    except ImportError as exc:
        print(
            f"Error: moviepy is not installed. Install it with: pip install moviepy>=1.0.3\n{exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Load video clips ---
    clips = load_clips(args.videos)

    # --- Concatenate clips ---
    if len(clips) == 1:
        combined = clips[0]
    else:
        combined = concatenate_videoclips(clips, method="compose")

    # --- Load audio ---
    audio_clip = None
    if args.audio:
        if not os.path.isfile(args.audio):
            print(f"Error: audio file not found: {args.audio}", file=sys.stderr)
            _cleanup(clips, audio_clip, combined if len(clips) > 1 else None)
            sys.exit(1)
        audio_clip = AudioFileClip(args.audio)

    # --- Duration matching ---
    if args.match_audio_duration and audio_clip is not None:
        combined = match_duration(combined, audio_clip.duration)

    # --- Attach audio to video ---
    if audio_clip is not None:
        # Trim audio if it exceeds video duration
        if audio_clip.duration > combined.duration:
            audio_clip = audio_clip.subclip(0, combined.duration)
        combined = combined.set_audio(audio_clip)

    # --- Ensure output directory exists ---
    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)

    # --- Export ---
    bitrate = QUALITY_BITRATE[args.quality]
    combined.write_videofile(
        args.output,
        fps=args.fps,
        codec="libx264",
        audio_codec="aac",
        bitrate=bitrate,
        logger="bar",  # show progress bar
    )

    # --- Cleanup ---
    _cleanup(clips, audio_clip, combined if len(clips) > 1 else None)

    print(f"Output saved to: {args.output}")


def _cleanup(clips, audio_clip, combined_clip):
    """Close all open clips to release file handles."""
    for clip in clips:
        try:
            clip.close()
        except Exception:
            pass
    if audio_clip is not None:
        try:
            audio_clip.close()
        except Exception:
            pass
    if combined_clip is not None:
        try:
            combined_clip.close()
        except Exception:
            pass


def main():
    args = parse_args()
    try:
        compose(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
