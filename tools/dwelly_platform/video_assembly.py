"""Assemble five real browser-capture segments into a fifty-second mobile demo.

Run ``python3 -m tools.dwelly_platform.video_assembly manifest.json``. Paths in
the JSON are relative to the manifest. Its exact keys are ``raw_video`` (WebM),
``output`` (new MP4), ``mode_label``, and ``segments``: five chronological objects
with ``start``, ``end`` (seconds), ``title``, and ``subtitle``. A segment may instead
specify ``clips: [{"start": 0, "end": 3}, ...]`` to omit recorded waits, with at
most eight chronological clips per segment. ``--validate-only``
checks the plan without rendering. No network or provider calls are made.

Long sections run faster; short sections hold their final captured frame. The
source is never modified. Each output frame includes an edited-capture notice.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


DISCLOSURE = 'Edited capture | waits shortened | local sandbox'
MAX_SOURCE_SECONDS = 3600


@dataclass(frozen=True)
class Clip:
    start: float
    end: float


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    title: str
    subtitle: str
    clips: tuple[Clip, ...]


@dataclass(frozen=True)
class AssemblyPlan:
    raw_video: Path
    output: Path
    mode_label: str
    segments: tuple[Segment, ...]
    duration_seconds: int = 50


def _caption(value, name, maximum):
    if (type(value) is not str or not value.strip() or len(value) > maximum
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError(f'{name} must be a nonempty single line, at most {maximum} characters')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ValueError(f'{name} must be valid UTF-8 text') from None
    return value.strip()


def _path(value, name, base_dir, suffix):
    if type(value) is not str or not value or '\x00' in value or '://' in value:
        raise ValueError(f'{name} must be a local {suffix} path')
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    path = path.resolve()
    if path.suffix.lower() != suffix:
        raise ValueError(f'{name} must have the {suffix} extension')
    return path


def validate_manifest(payload, base_dir=None):
    """Validate bounded inputs and resolve local paths without modifying them."""
    if type(payload) is not dict or set(payload) != {
            'raw_video', 'output', 'mode_label', 'segments'}:
        raise ValueError('manifest requires exactly raw_video, output, mode_label, segments')
    base_dir = Path(base_dir or Path.cwd()).resolve()
    raw = _path(payload['raw_video'], 'raw_video', base_dir, '.webm')
    output = _path(payload['output'], 'output', base_dir, '.mp4')
    if not raw.is_file() or raw.stat().st_size == 0 or raw.stat().st_size > 2 * 1024**3:
        raise ValueError('raw_video must be an existing nonempty WebM smaller than 2 GiB')
    if output.exists():
        raise FileExistsError(f'refusing to overwrite existing output: {output}')
    if not output.parent.is_dir():
        raise ValueError('output parent directory must already exist')
    mode = _caption(payload['mode_label'], 'mode_label', 80)
    items = payload['segments']
    if type(items) is not list or len(items) != 5:
        raise ValueError('exactly five segments are required')
    segments = []
    previous_end = 0.0
    for index, item in enumerate(items):
        if type(item) is not dict or set(item) not in (
                {'start', 'end', 'title', 'subtitle'}, {'clips', 'title', 'subtitle'}):
            raise ValueError(f'segment {index + 1} requires title, subtitle and start/end or clips')
        cuts = item.get('clips', [{'start': item.get('start'), 'end': item.get('end')}])
        if type(cuts) is not list or not 1 <= len(cuts) <= 8:
            raise ValueError('each stage requires between one and eight clips')
        clips = []
        for cut in cuts:
            if type(cut) is not dict or set(cut) != {'start', 'end'}:
                raise ValueError('each clip requires exactly start and end')
            start, end = cut['start'], cut['end']
            if (type(start) not in (int, float) or type(end) not in (int, float)
                    or not math.isfinite(start) or not math.isfinite(end)
                    or not previous_end <= start < end <= MAX_SOURCE_SECONDS):
                raise ValueError('segment times must be finite, ordered, nonoverlapping, within one hour')
            clips.append(Clip(float(start), float(end)))
            previous_end = end
        segments.append(Segment(clips[0].start, clips[-1].end,
                                _caption(item['title'], 'title', 64),
                                _caption(item['subtitle'], 'subtitle', 110), tuple(clips)))
    return AssemblyPlan(raw, output, mode, tuple(segments))


def _executable(name):
    preferred = Path('/opt/homebrew/bin') / name
    candidate = str(preferred) if preferred.is_file() else shutil.which(name)
    if not candidate:
        raise ValueError(f'{name} is required')
    return candidate


def write_caption_frame(plan, segment, directory):
    """Render static brand/caption pixels; browser pixels come only from WebM."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new('RGB', (1080, 1920), '#173B32')
    draw = ImageDraw.Draw(image)
    font_path = next((path for path in (
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    ) if Path(path).is_file()), None)

    def text(value, y, size, fill):
        while True:
            font = (ImageFont.truetype(font_path, size) if font_path
                    else ImageFont.load_default(size=size))
            if draw.textbbox((0, 0), value, font=font)[2] <= 960 or size <= 14:
                break
            size -= 1
        draw.text((60, y), value, font=font, fill=fill)

    text(segment.title, 26, 42, '#F5F3E9')
    text(segment.subtitle, 93, 28, '#D4E5DA')
    draw.rectangle((60, 160, 1019, 1799), fill='#F5F3E9')
    text(plan.mode_label, 1826, 27, '#F5F3E9')
    text(DISCLOSURE, 1870, 23, '#D4E5DA')
    output = Path(directory) / 'caption.png'
    image.save(output)
    return output


def build_segment_command(plan, segment, output, caption_frame, *, ffmpeg=None):
    """Return shell-free FFmpeg argv for exactly 300 frames of one segment."""
    duration = sum(clip.end - clip.start for clip in segment.clips)
    speed = min(1.0, 10.0 / duration)
    sources = []
    for clip in segment.clips:
        sources.extend(['-ss', f'{clip.start:.12g}', '-t', f'{clip.end - clip.start:.12g}',
                        '-protocol_whitelist', 'file,pipe', '-i', str(plan.raw_video)])
    if len(segment.clips) == 1:
        cuts, source = '', '[0:v]'
    else:
        cuts = ''.join(f'[{i}:v]setpts=PTS-STARTPTS,setsar=1[cut{i}];'
                       for i in range(len(segment.clips)))
        cuts += ''.join(f'[cut{i}]' for i in range(len(segment.clips)))
        cuts += f'concat=n={len(segment.clips)}:v=1:a=0[joined];'
        source = '[joined]'
    graph = (
        cuts + f'{source}setpts={speed:.12g}*(PTS-STARTPTS),'
        'scale=960:1640:force_original_aspect_ratio=decrease,'
        'pad=960:1640:(ow-iw)/2:(oh-ih)/2:color=0xF5F3E9,setsar=1,'
        'fps=30,tpad=stop_mode=clone:stop_duration=10,trim=duration=10[screen];'
        f'[{len(segment.clips)}:v][screen]overlay=60:160:shortest=1,format=yuv420p[out]'
    )
    return [ffmpeg or _executable('ffmpeg'), '-hide_banner', '-loglevel', 'error',
            '-nostdin', '-n', *sources,
            '-loop', '1', '-framerate', '30', '-i', str(caption_frame),
            '-filter_complex', graph, '-map', '[out]', '-an', '-r', '30',
            '-frames:v', '300', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]


def validate_probe(plan, probe, *, final=False):
    """Reject bad source geometry/ranges and nonconforming rendered output."""
    try:
        videos = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
        if len(videos) != 1:
            raise ValueError('exactly one video stream is required')
        video = videos[0]
        duration = float(probe['format']['duration'])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('invalid video duration')
        size = (video['width'], video['height'])
        if final:
            if (size != (1080, 1920) or Fraction(video['r_frame_rate']) != 30
                    or int(video['nb_frames']) != 1500 or abs(duration - 50) > 0.001):
                raise ValueError('final must be 1080x1920, 1500 frames, 30 fps, exactly 50 seconds')
        elif (size != (390, 666) or duration > MAX_SOURCE_SECONDS
              or plan.segments[-1].end > duration + 1 / 30):
            raise ValueError('source must be 390x666 and contain all planned segment times')
    except (KeyError, TypeError, ZeroDivisionError, OverflowError) as error:
        raise ValueError('invalid ffprobe metadata') from error


def _run(argv, timeout):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                            check=False, shell=False)
    if result.returncode:
        raise ValueError(f'{Path(argv[0]).name} failed: {result.stderr[-4000:].strip()}')
    return result.stdout


def _probe(path, ffprobe):
    return json.loads(_run([
        ffprobe, '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-show_entries', 'stream=codec_type,width,height,r_frame_rate,nb_frames:format=duration',
        '-of', 'json', str(path),
    ], 30))


def assemble_video(plan):
    """Render locally, verify, then atomically publish without replacing files."""
    if plan.output.exists():
        raise FileExistsError(f'refusing to overwrite existing output: {plan.output}')
    ffmpeg, ffprobe = _executable('ffmpeg'), _executable('ffprobe')
    validate_probe(plan, _probe(plan.raw_video, ffprobe))
    with tempfile.TemporaryDirectory(prefix='proofkey-capture-', dir=plan.output.parent) as workspace:
        directory = Path(workspace)
        clips = []
        for index, segment in enumerate(plan.segments):
            frame = write_caption_frame(plan, segment, directory)
            clip = directory / f'clip-{index}.mp4'
            _run(build_segment_command(plan, segment, clip, frame, ffmpeg=ffmpeg), 600)
            clips.append(clip)
        listing = directory / 'concat.txt'
        # Only generated, fixed ASCII basenames enter concat syntax.
        listing.write_text(''.join(f"file '{clip.name}'\n" for clip in clips), encoding='utf-8')
        combined = directory / 'assembled.mp4'
        _run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
              '-f', 'concat', '-safe', '1', '-i', str(listing), '-map', '0:v:0',
              '-an', '-c', 'copy', '-movflags', '+faststart', str(combined)], 60)
        validate_probe(plan, _probe(combined, ffprobe), final=True)
        # Same-filesystem link is atomic and raises if another process created
        # the requested output while rendering; source WebM is never written.
        os.link(combined, plan.output)
    return plan.output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.manifest.stat().st_size > 64 * 1024:
            raise ValueError('manifest must be smaller than 64 KiB')
        payload = json.loads(args.manifest.read_text(encoding='utf-8'))
        plan = validate_manifest(payload, args.manifest.resolve().parent)
        if args.validate_only:
            result = {'valid': True, 'raw_video': str(plan.raw_video),
                      'output': str(plan.output), 'segments': 5, 'seconds': 50,
                      'width': 1080, 'height': 1920, 'fps': 30,
                      'mode_label': plan.mode_label, 'disclosure': DISCLOSURE}
        else:
            result = {'output': str(assemble_video(plan)), 'seconds': 50, 'frames': 1500}
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'video assembly: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
