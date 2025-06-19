import json
from pipecat.frames.frames import EndFrame, Frame, InterimTranscriptionFrame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.utils.string import match_endofsentence


class JSONSentenceAggregator(FrameProcessor):
    """Aggregate text until a complete sentence or JSON object is received."""

    def __init__(self):
        super().__init__()
        self._aggregation = ""

    def _is_complete_json(self, text: str) -> bool:
        text = text.strip()
        if not text or text[0] not in "{[":
            return False
        try:
            _, idx = json.JSONDecoder().raw_decode(text)
            return idx == len(text)
        except json.JSONDecodeError:
            return False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InterimTranscriptionFrame):
            return

        if isinstance(frame, TextFrame):
            self._aggregation += frame.text
            while True:
                if self._is_complete_json(self._aggregation):
                    await self.push_frame(TextFrame(self._aggregation.strip()))
                    self._aggregation = ""
                else:
                    eos = match_endofsentence(self._aggregation)
                    if eos:
                        await self.push_frame(TextFrame(self._aggregation[:eos]))
                        self._aggregation = self._aggregation[eos:]
                        continue
                break
        elif isinstance(frame, EndFrame):
            if self._aggregation:
                await self.push_frame(TextFrame(self._aggregation))
                self._aggregation = ""
            await self.push_frame(frame)
        else:
            await self.push_frame(frame, direction)
