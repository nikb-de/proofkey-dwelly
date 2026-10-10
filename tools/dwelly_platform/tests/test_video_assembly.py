"""Deterministic browser-capture assembly contracts; no provider calls."""
import copy
import importlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

try:
    assembly = importlib.import_module('tools.dwelly_platform.video_assembly')
except ModuleNotFoundError:
    assembly = None


class VideoAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(assembly, 'deterministic video assembler must exist')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.raw = self.directory / 'raw capture.webm'
        self.raw.write_bytes(b'preserved recording fixture')
        self.payload = {
            'raw_video': self.raw.name,
            'output': 'edited capture.mp4',
            'mode_label': 'Synthetic scenario | local sandbox',
            'segments': [
                {'start': start, 'end': end, 'title': f'Step {index + 1}',
                 'subtitle': 'Recorded product interface'}
                for index, (start, end) in enumerate(
                    [(0, 3), (4, 14), (15, 35), (36, 42), (43, 60)])
            ],
        }

    def plan(self, payload=None):
        return assembly.validate_manifest(payload or self.payload, self.directory)

    def test_relative_paths_resolve_against_manifest_directory(self):
        plan = self.plan()
        self.assertEqual(plan.raw_video, self.raw)
        self.assertEqual(plan.output, self.directory / 'edited capture.mp4')
        self.assertEqual(len(plan.segments), 5)
        self.assertEqual(plan.duration_seconds, 50)

    def test_rejects_missing_unknown_or_wrong_typed_manifest_fields(self):
        for change in ({'extra': True}, {'segments': []}, {'mode_label': ''},
                       {'mode_label': 'line\nbreak'}, {'raw_video': 42}):
            with self.subTest(change=change):
                payload = copy.deepcopy(self.payload)
                payload.update(change)
                with self.assertRaises(ValueError):
                    self.plan(payload)
        payload = copy.deepcopy(self.payload)
        del payload['output']
        with self.assertRaises(ValueError):
            self.plan(payload)

    def test_rejects_invalid_or_overlapping_segment_times(self):
        for field, value in [('start', -1), ('start', True), ('end', float('nan')),
                             ('end', float('inf')), ('end', 0), ('end', 3601)]:
            with self.subTest(field=field, value=value):
                payload = copy.deepcopy(self.payload)
                payload['segments'][0][field] = value
                with self.assertRaises(ValueError):
                    self.plan(payload)
        payload = copy.deepcopy(self.payload)
        payload['segments'][1]['start'] = 2
        with self.assertRaises(ValueError):
            self.plan(payload)

    def test_rejects_missing_source_and_existing_output_without_modifying_them(self):
        raw_bytes = self.raw.read_bytes()
        output = self.directory / 'edited capture.mp4'
        output.write_bytes(b'existing final')
        with self.assertRaises(FileExistsError):
            self.plan()
        self.assertEqual(output.read_bytes(), b'existing final')
        self.assertEqual(self.raw.read_bytes(), raw_bytes)
        output.unlink()
        self.raw.unlink()
        with self.assertRaises(ValueError):
            self.plan()

    def test_rejects_unbounded_caption_text_and_wrong_file_types(self):
        for change in ({'mode_label': 'x' * 81}, {'output': 'edited.mov'},
                       {'raw_video': 'https://example.com/recording.webm'}):
            with self.subTest(change=change):
                payload = copy.deepcopy(self.payload)
                payload.update(change)
                with self.assertRaises(ValueError):
                    self.plan(payload)
        payload = copy.deepcopy(self.payload)
        payload['segments'][0]['title'] = 'x' * 65
        with self.assertRaises(ValueError):
            self.plan(payload)

    def test_command_compresses_long_recording_sections_and_freezes_short_ones(self):
        plan = self.plan()
        frame = self.directory / 'caption.png'
        long_command = assembly.build_segment_command(
            plan, plan.segments[2], self.directory / 'clip.mp4', frame,
            ffmpeg='/opt/homebrew/bin/ffmpeg')
        short_command = assembly.build_segment_command(
            plan, plan.segments[0], self.directory / 'clip.mp4', frame,
            ffmpeg='/opt/homebrew/bin/ffmpeg')
        long_filter = long_command[long_command.index('-filter_complex') + 1]
        short_filter = short_command[short_command.index('-filter_complex') + 1]
        self.assertIn('setpts=0.5*(PTS-STARTPTS)', long_filter)
        self.assertIn('setpts=1*(PTS-STARTPTS)', short_filter)
        self.assertIn('tpad=stop_mode=clone:stop_duration=10', short_filter)
        self.assertIn('scale=960:1640', long_filter)
        self.assertIn('overlay=60:160', long_filter)
        self.assertEqual(long_command[long_command.index('-r') + 1], '30')
        self.assertIn(str(frame), long_command)
        self.assertIn('-n', long_command)
        self.assertEqual(long_command[long_command.index('-frames:v') + 1], '300')
        self.assertEqual(long_command[long_command.index('-i') + 1], str(self.raw))
        self.assertEqual(long_command[long_command.index('-t') + 1], '20')
        self.assertEqual(long_command[-1], str(self.directory / 'clip.mp4'))

    def test_caption_punctuation_renders_to_png_without_entering_filter_source(self):
        payload = copy.deepcopy(self.payload)
        payload['segments'][0]['title'] = "Tenant's 100%: ${HOME}; [case]"
        plan = self.plan(payload)
        frame = assembly.write_caption_frame(plan, plan.segments[0], self.directory)
        with Image.open(frame) as image:
            self.assertEqual(image.size, (1080, 1920))
            self.assertEqual(image.format, 'PNG')
            self.assertEqual(image.getpixel((0, 0)), (23, 59, 50))
            self.assertGreater(len(image.crop((60, 25, 1020, 100)).getcolors(100000)), 1)
        command = assembly.build_segment_command(
            plan, plan.segments[0], self.directory / 'clip.mp4', frame)
        self.assertNotIn(payload['segments'][0]['title'], json.dumps(command))

    def test_probe_validation_rejects_out_of_range_capture_and_wrong_final(self):
        plan = self.plan()
        assembly.validate_probe(plan, {
            'streams': [{'codec_type': 'video', 'width': 390, 'height': 666}],
            'format': {'duration': '60.01'},
        })
        with self.assertRaises(ValueError):
            assembly.validate_probe(plan, {
                'streams': [{'codec_type': 'video', 'width': 390, 'height': 666}],
                'format': {'duration': '59'},
            })
        correct = {'streams': [{'codec_type': 'video', 'width': 1080, 'height': 1920,
                               'r_frame_rate': '30/1', 'nb_frames': '1500'}],
                   'format': {'duration': '50.000000'}}
        assembly.validate_probe(plan, correct, final=True)
        incorrect = copy.deepcopy(correct)
        incorrect['streams'][0]['nb_frames'] = '1499'
        with self.assertRaises(ValueError):
            assembly.validate_probe(plan, incorrect, final=True)

    def test_stage_can_splice_recorded_spans_before_padding_to_ten_seconds(self):
        payload = copy.deepcopy(self.payload)
        payload['segments'][0] = {
            'clips': [{'start': 0, 'end': 1}, {'start': 2, 'end': 3}],
            'title': 'Selected capture spans', 'subtitle': 'Waiting omitted',
        }
        plan = self.plan(payload)
        command = assembly.build_segment_command(
            plan, plan.segments[0], self.directory / 'clip.mp4',
            self.directory / 'caption.png')
        graph = command[command.index('-filter_complex') + 1]
        self.assertEqual(command.count(str(self.raw)), 2)
        self.assertIn('concat=n=2:v=1:a=0', graph)
        self.assertIn('[2:v][screen]overlay=60:160', graph)
        self.assertIn('setpts=1*(PTS-STARTPTS)', graph)

    def test_spliced_stages_reject_overlap_empty_or_excessive_cuts(self):
        for clips in ([], [{'start': 0, 'end': 2}, {'start': 1, 'end': 3}],
                      [{'start': i / 10, 'end': (i + 1) / 10} for i in range(9)]):
            with self.subTest(clips=clips):
                payload = copy.deepcopy(self.payload)
                payload['segments'][0] = {
                    'clips': clips, 'title': 'Stage', 'subtitle': 'Selected spans'}
                with self.assertRaises(ValueError):
                    self.plan(payload)


if __name__ == '__main__':
    unittest.main()
