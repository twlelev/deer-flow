---
name: video-compose
description: Use this skill to merge and compose video clips with audio tracks using MoviePy. Handles combining multiple video segments, replacing or mixing audio, adjusting clip durations to match audio length, and exporting the final video. Ideal for the final step of AI content creation pipelines after generating individual clips and narration audio.
license: MIT
version: 1.0.0
---

# Video Compose Skill

## Overview

This skill uses MoviePy to compose a final video by merging video clips and audio tracks. It is designed as the final step in AI content creation pipelines where:

1. Individual video clips have been generated (via I2V or T2V workflows)
2. Narration audio has been synthesized (via TTS workflows)
3. These assets need to be assembled into a cohesive final video

## Core Capabilities

- **Merge clips**: Concatenate multiple video clips in sequence
- **Audio mixing**: Replace video audio with TTS narration, or mix narration over background music
- **Duration matching**: Automatically stretch/trim clips to match total audio length
- **Format output**: Export as MP4 (H.264) with configurable quality

## Input/Output

**Input files** (located in `/mnt/user-data/uploads/` or as absolute paths):
- Video clips: `.mp4`, `.mov`, `.avi`, `.webm`
- Audio track: `.mp3`, `.wav`, `.flac`, `.m4a`

**Output file** (saved to `/mnt/user-data/outputs/`):
- `composed_video.mp4` (or custom name)

## Usage

### Basic: Merge clips + add audio
```bash
python /mnt/skills/custom/video-compose/scripts/compose.py \
  --videos /mnt/user-data/uploads/clip1.mp4 /mnt/user-data/uploads/clip2.mp4 \
  --audio /mnt/user-data/uploads/narration.mp3 \
  --output /mnt/user-data/outputs/composed_video.mp4
```

### With duration matching (clips stretched/trimmed to match audio)
```bash
python /mnt/skills/custom/video-compose/scripts/compose.py \
  --videos /mnt/user-data/uploads/clip1.mp4 /mnt/user-data/uploads/clip2.mp4 \
  --audio /mnt/user-data/uploads/narration.mp3 \
  --output /mnt/user-data/outputs/final.mp4 \
  --match-audio-duration
```

### Single video + replace audio
```bash
python /mnt/skills/custom/video-compose/scripts/compose.py \
  --videos /mnt/user-data/uploads/generated_video.mp4 \
  --audio /mnt/user-data/uploads/tts_audio.mp3 \
  --output /mnt/user-data/outputs/with_audio.mp4
```

### No audio (concatenate only)
```bash
python /mnt/skills/custom/video-compose/scripts/compose.py \
  --videos /mnt/user-data/uploads/clip1.mp4 /mnt/user-data/uploads/clip2.mp4 \
  --output /mnt/user-data/outputs/merged.mp4
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--videos` | Yes | - | One or more video file paths (space-separated) |
| `--audio` | No | - | Audio file path to use as final audio track |
| `--output` | Yes | - | Output video file path |
| `--match-audio-duration` | No | False | Stretch/trim video clips to match audio duration |
| `--fps` | No | 25 | Output frames per second |
| `--quality` | No | medium | Output quality: `low` / `medium` / `high` |

## Workflow Integration

This skill is typically used as the **final step** in content creation:

```
Step 1: Generate video clips via ComfyUI (I2V or T2V)
         → /mnt/user-data/outputs/clip1.mp4

Step 2: Generate narration via ComfyUI (TTS)
         → /mnt/user-data/outputs/narration.mp3

Step 3: Compose final video using this skill
         → python compose.py --videos clip1.mp4 --audio narration.mp3 --output final.mp4

Step 4: Present final video to user
         → Use present_files tool
```

## Error Handling

The script exits with code 0 on success and prints the output path.
On error, it exits with code 1 and prints the error message to stderr.

## Dependencies

- `moviepy>=1.0.3` - Video editing library
- `ffmpeg` - Required by MoviePy (must be installed on system)
