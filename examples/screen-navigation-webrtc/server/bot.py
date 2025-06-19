import os
import re

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    TextFrame,
    TranscriptionMessage,
    TransportMessageFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from json_sentence_aggregator import JSONSentenceAggregator
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport

load_dotenv(override=True)

# Read system prompt from file specified in the environment
SYSTEM_PROMPT_FILE = os.getenv("SYSTEM_PROMPT_FILE", "system_prompt.txt")
try:
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    SYSTEM_PROMPT = "You are a helpful assistant."  # Fallback prompt

# Simple command patterns for demonstration
COMMAND_PATTERNS = [
    (re.compile(r"\bscroll up\b", re.I), lambda m: {"action": "scroll_up"}),
    (re.compile(r"\bscroll down\b", re.I), lambda m: {"action": "scroll_down"}),
    (re.compile(r"\bgo back\b", re.I), lambda m: {"action": "go_back"}),
    (
        re.compile(r"\bopen (?P<target>.+)", re.I),
        lambda m: {"action": "open", "target": m.group("target").strip()},
    ),
    (
        re.compile(r"\bclick (?P<target>.+)", re.I),
        lambda m: {"action": "click", "target": m.group("target").strip()},
    ),
]


class LLMOutputHandler(FrameProcessor):
    """Send completed sentences from the LLM to the client."""

    def __init__(self, transport: SmallWebRTCTransport):
        super().__init__()
        self._transport = transport

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            await self._transport.output().send_message(
                TransportMessageFrame(message={"response": frame.text})
            )
        else:
            await self.push_frame(frame, direction)


def parse_command(text: str):
    for pattern, builder in COMMAND_PATTERNS:
        match = pattern.search(text)
        if match:
            return builder(match)
    return None


async def run_bot(webrtc_connection):
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=False,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    transcript = TranscriptProcessor()

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )

    context = OpenAILLMContext([{"role": "system", "content": SYSTEM_PROMPT}])
    context_aggregator = llm.create_context_aggregator(context)

    sentence_agg = JSONSentenceAggregator()
    llm_handler = LLMOutputHandler(transport)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            transcript.user(),
            context_aggregator.user(),
            llm,
            sentence_agg,
            llm_handler,
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=False),
    )

    system_manifest_received = False

    @transport.event_handler("on_app_message")
    async def on_app_message(transport, message):
        nonlocal system_manifest_received
        if (
            isinstance(message, dict)
            and message.get("role") == "system"
            and not system_manifest_received
        ):
            logger.debug("Received system manifest from client")
            context.add_message({"role": "system", "content": message.get("content", "")})
            system_manifest_received = True

    @transcript.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        for msg in frame.messages:
            if isinstance(msg, TranscriptionMessage) and msg.role == "user":
                await transport.output().send_message(
                    TransportMessageFrame(
                        message={"transcript": msg.content, "timestamp": msg.timestamp}
                    )
                )
                cmd = parse_command(msg.content.lower())
                if cmd:
                    logger.info(f"Detected command: {cmd}")
                    await transport.output().send_message(
                        TransportMessageFrame(message={"command": cmd})
                    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
