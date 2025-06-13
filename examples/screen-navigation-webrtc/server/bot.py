import os
import re

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TranscriptionMessage, TransportMessageFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport

load_dotenv(override=True)

# Simple command patterns for demonstration
COMMAND_PATTERNS = [
    (re.compile(r"\bscroll up\b", re.I), lambda m: {"action": "scroll_up"}),
    (re.compile(r"\bscroll down\b", re.I), lambda m: {"action": "scroll_down"}),
    (re.compile(r"\bgo back\b", re.I), lambda m: {"action": "go_back"}),
    (re.compile(r"\bopen (?P<target>.+)", re.I), lambda m: {"action": "open", "target": m.group("target").strip()}),
    (re.compile(r"\bclick (?P<target>.+)", re.I), lambda m: {"action": "click", "target": m.group("target").strip()}),
]


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

    pipeline = Pipeline([
        transport.input(),
        stt,
        transcript.user(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=False),
    )

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
