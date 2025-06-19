import unittest

from pipecat.frames.frames import TextFrame
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
from json_sentence_aggregator import JSONSentenceAggregator  # noqa: E402
from pipecat.tests.utils import run_test


class TestJSONSentenceAggregator(unittest.IsolatedAsyncioTestCase):
    async def test_json_detection(self):
        aggregator = JSONSentenceAggregator()

        frames_to_send = [
            TextFrame("{"),
            TextFrame('"kind": "need",'),
            TextFrame(' "id": "123"'),
            TextFrame("}"),
        ]

        expected_down_frames = [TextFrame]

        (received_down, _) = await run_test(
            aggregator,
            frames_to_send=frames_to_send,
            expected_down_frames=expected_down_frames,
        )

        assert received_down[0].text == '{"kind": "need", "id": "123"}'

    async def test_sentence_and_json(self):
        aggregator = JSONSentenceAggregator()

        frames_to_send = [
            TextFrame("Hello world."),
            TextFrame(" {"),
            TextFrame('"kind": "need"'),
            TextFrame(', "id": "1"'),
            TextFrame("}"),
        ]

        expected_down_frames = [TextFrame, TextFrame]

        (received_down, _) = await run_test(
            aggregator,
            frames_to_send=frames_to_send,
            expected_down_frames=expected_down_frames,
        )

        assert received_down[0].text == "Hello world."
        assert received_down[1].text == '{"kind": "need", "id": "1"}'
