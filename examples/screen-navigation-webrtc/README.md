# Screen Navigation with WebRTC

This example demonstrates how to use Pipecat with WebRTC to receive live speech commands and
send back screen navigation actions in real-time. Speech is transcribed using an external
service (Deepgram in this demo) and simple patterns are matched to emit commands such as
`scroll_up`, `scroll_down`, `click`, etc.

## Quick Start

### 1. Start the server

1. Create and activate a virtual environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies
   ```bash
   pip install -r server/requirements.txt
   ```
3. Configure environment variables
   ```bash
   cp server/env.example server/.env
   ```
   Edit `.env` and add your API keys. At minimum set `DEEPGRAM_API_KEY`
   and `OPENAI_API_KEY`. You can also override `OPENAI_MODEL` or
   `SYSTEM_PROMPT_FILE` if desired.
4. Run the server (listening on all interfaces)
   ```bash
   python server/server.py --host 0.0.0.0
   ```

### 2. Connect with your own WebRTC client

Use a custom WebRTC client to exchange SDP with the server's `/api/offer` endpoint.
Once connected, audio will stream to the server and JSON messages containing
transcripts and detected commands are sent back over the data channel.
Before the connection is fully established, your client can send a JSON object
with `{"role": "system", "content": "..."}` to provide an initial manifest for
the LLM conversation. This message is appended to the conversation history
before any user input is processed.

## Requirements

- Python 3.10+
- A WebRTC-capable client (browser or custom application)
- A Deepgram API key
- An OpenAI API key

## Build and test the Docker image

The Docker image listens on `0.0.0.0:7860` and exposes port `7860`.

```bash
docker build -t screen-navigation-webrtc .
docker run --env-file server/.env -p 7860:7860 screen-navigation-webrtc
```
