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
   Edit `.env` and add your Deepgram API key.
4. Run the server (listening on all interfaces)
   ```bash
   python server/server.py --host 0.0.0.0
   ```

### 2. Connect from a browser

Open `http://localhost:7860` (replace `localhost` with your host IP if running remotely) and allow microphone access. Speak commands like
"scroll down" or "click search box". The server sends back JSON messages with the
transcript of each utterance and any detected commands.

## Requirements

- Python 3.10+
- A modern browser with WebRTC support
- A Deepgram API key

## Build and test the Docker image

The Docker image listens on `0.0.0.0:7860` and exposes port `7860`.

```bash
docker build -t screen-navigation-webrtc .
docker run --env-file server/.env -p 7860:7860 screen-navigation-webrtc
```
