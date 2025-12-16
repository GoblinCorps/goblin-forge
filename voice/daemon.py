#!/usr/bin/env python3
"""
Goblin Forge Voice Daemon

A background service that captures voice commands via Whisper STT
and sends them to gforge via Unix socket IPC.

Requires:
    pip install faster-whisper sounddevice numpy evdev
"""

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import socket
import struct
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable

import numpy as np
import sounddevice as sd

# Optional imports with graceful fallback
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    WhisperModel = None

try:
    from evdev import InputDevice, ecodes, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('gforge-voice')


@dataclass
class Config:
    """Voice daemon configuration"""
    socket_path: str = "/tmp/gforge-voice.sock"
    model_size: str = "tiny"  # tiny, base, small, medium, large
    device: str = "cpu"  # cpu, cuda, auto
    sample_rate: int = 16000
    channels: int = 1
    hotkey_device: Optional[str] = None  # Auto-detect if None
    hotkey_key: str = "KEY_SCROLLLOCK"  # Default hotkey
    min_recording_duration: float = 0.5  # Minimum seconds to record
    max_recording_duration: float = 30.0  # Maximum seconds to record
    silence_threshold: float = 0.01  # RMS threshold for silence detection
    silence_duration: float = 1.5  # Seconds of silence to stop recording
    feedback_sounds: bool = True  # Play sounds for start/stop


class CommandParser:
    """Parse voice transcriptions into gforge commands"""

    PATTERNS = [
        # Spawn commands
        (r"spawn (?:a )?(?:new )?(?:goblin )?(?:called |named )?(\w+)(?: with | using )?(?:agent )?(\w+)?(?:(?: for | to )(.+))?",
         lambda m: {"action": "spawn", "name": m.group(1), "agent": m.group(2) or "claude", "task": m.group(3)}),

        (r"create (?:a )?(?:goblin )?(?:called |named )?(\w+)",
         lambda m: {"action": "spawn", "name": m.group(1), "agent": "claude"}),

        # Attach commands
        (r"attach (?:to )?(?:goblin )?(\w+)",
         lambda m: {"action": "attach", "name": m.group(1)}),

        (r"go to (?:goblin )?(\w+)",
         lambda m: {"action": "attach", "name": m.group(1)}),

        # Stop/Kill commands
        (r"stop (?:goblin )?(\w+)",
         lambda m: {"action": "stop", "name": m.group(1)}),

        (r"kill (?:goblin )?(\w+)",
         lambda m: {"action": "kill", "name": m.group(1)}),

        (r"terminate (?:goblin )?(\w+)",
         lambda m: {"action": "kill", "name": m.group(1)}),

        # List commands
        (r"(?:list|show) (?:all )?goblins",
         lambda m: {"action": "list"}),

        (r"what goblins (?:are )?running",
         lambda m: {"action": "list"}),

        # Status commands
        (r"(?:show |what's the )?status",
         lambda m: {"action": "status"}),

        # Diff commands
        (r"(?:show )?diff (?:for |of )?(?:goblin )?(\w+)?",
         lambda m: {"action": "diff", "name": m.group(1)}),

        (r"what (?:did|has) (\w+) (?:change|done)",
         lambda m: {"action": "diff", "name": m.group(1)}),

        # Git commands
        (r"commit (?:goblin )?(\w+)? ?(?:with message )?(.+)?",
         lambda m: {"action": "commit", "name": m.group(1), "message": m.group(2)}),

        (r"push (?:goblin )?(\w+)?",
         lambda m: {"action": "push", "name": m.group(1)}),

        # Task commands
        (r"(?:tell|send|ask) (?:goblin )?(\w+) (?:to )?(.+)",
         lambda m: {"action": "task", "name": m.group(1), "description": m.group(2)}),

        # Open commands
        (r"open (?:goblin )?(\w+) (?:in )?(?:editor|code|vim|nvim)",
         lambda m: {"action": "edit", "name": m.group(1)}),

        # Dashboard
        (r"(?:open |show |launch )?(?:the )?dashboard",
         lambda m: {"action": "top"}),

        (r"(?:open |show |launch )?(?:the )?tui",
         lambda m: {"action": "top"}),

        # Help
        (r"(?:show )?help",
         lambda m: {"action": "help"}),

        # Exit/Quit
        (r"(?:exit|quit|stop)(?: listening)?",
         lambda m: {"action": "exit_voice"}),
    ]

    def parse(self, text: str) -> dict:
        """Parse transcribed text into a command"""
        text = text.lower().strip()

        # Remove filler words
        text = re.sub(r'\b(um|uh|like|you know|actually)\b', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        for pattern, handler in self.PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                result = handler(match)
                # Clean up None values
                result = {k: v for k, v in result.items() if v is not None}
                result["raw"] = text
                return result

        # No pattern matched - return raw text
        return {"action": "unknown", "raw": text}


class AudioRecorder:
    """Handle audio recording with silence detection"""

    def __init__(self, config: Config):
        self.config = config
        self.recording = False
        self.audio_data = []
        self.stream = None

    def start(self):
        """Start recording audio"""
        self.recording = True
        self.audio_data = []

        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            if self.recording:
                self.audio_data.append(indata.copy())

        self.stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype='float32',
            callback=callback
        )
        self.stream.start()
        logger.info("Recording started")

    def stop(self) -> np.ndarray:
        """Stop recording and return audio data"""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_data:
            return np.array([])

        audio = np.concatenate(self.audio_data)
        logger.info(f"Recording stopped: {len(audio) / self.config.sample_rate:.2f}s")
        return audio

    def is_silence(self, audio: np.ndarray) -> bool:
        """Check if audio segment is silence"""
        if len(audio) == 0:
            return True
        rms = np.sqrt(np.mean(audio ** 2))
        return rms < self.config.silence_threshold


class VoiceDaemon:
    """Main voice daemon service"""

    def __init__(self, config: Config):
        self.config = config
        self.parser = CommandParser()
        self.recorder = AudioRecorder(config)
        self.model: Optional[WhisperModel] = None
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.recording_active = False

    async def start(self):
        """Start the voice daemon"""
        self.running = True

        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: self._shutdown())

        # Initialize Whisper model
        await self._init_model()

        # Create socket
        await self._init_socket()

        # Start hotkey listener
        asyncio.create_task(self._hotkey_listener())

        # Start socket server
        asyncio.create_task(self._socket_server())

        logger.info(f"Voice daemon started (model={self.config.model_size})")
        logger.info(f"Listening on {self.config.socket_path}")
        logger.info(f"Hotkey: {self.config.hotkey_key}")

        # Keep running
        while self.running:
            await asyncio.sleep(1)

    async def _init_model(self):
        """Initialize Whisper model"""
        if not WHISPER_AVAILABLE:
            logger.warning("faster-whisper not installed - transcription disabled")
            return

        logger.info(f"Loading Whisper model: {self.config.model_size}...")

        # Determine compute type based on device
        compute_type = "float32"
        if self.config.device == "cuda":
            compute_type = "float16"
        elif self.config.device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    self.config.device = "cuda"
                    compute_type = "float16"
                else:
                    self.config.device = "cpu"
            except ImportError:
                self.config.device = "cpu"

        self.model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=compute_type
        )
        logger.info(f"Model loaded on {self.config.device}")

    async def _init_socket(self):
        """Initialize Unix socket"""
        # Remove existing socket
        socket_path = Path(self.config.socket_path)
        if socket_path.exists():
            socket_path.unlink()

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(str(socket_path))
        self.socket.listen(5)
        self.socket.setblocking(False)

    async def _hotkey_listener(self):
        """Listen for hotkey presses"""
        if not EVDEV_AVAILABLE:
            logger.warning("evdev not installed - hotkey disabled, use socket control")
            return

        # Find keyboard device
        device = None
        if self.config.hotkey_device:
            device = InputDevice(self.config.hotkey_device)
        else:
            for dev_path in list_devices():
                dev = InputDevice(dev_path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps:
                    # Check if it's a keyboard
                    keys = caps[ecodes.EV_KEY]
                    if ecodes.KEY_A in keys and ecodes.KEY_Z in keys:
                        device = dev
                        break

        if not device:
            logger.warning("No keyboard device found - hotkey disabled")
            return

        logger.info(f"Hotkey listener attached to {device.name}")

        # Get key code
        key_code = getattr(ecodes, self.config.hotkey_key, ecodes.KEY_SCROLLLOCK)

        async for event in device.async_read_loop():
            if event.type == ecodes.EV_KEY and event.code == key_code:
                if event.value == 1:  # Key down
                    await self._toggle_recording()

    async def _toggle_recording(self):
        """Toggle recording state"""
        if not self.recording_active:
            await self._start_recording()
        else:
            await self._stop_recording()

    async def _start_recording(self):
        """Start recording voice"""
        self.recording_active = True
        self.recorder.start()

        if self.config.feedback_sounds:
            await self._play_sound("start")

    async def _stop_recording(self):
        """Stop recording and process"""
        self.recording_active = False
        audio = self.recorder.stop()

        if self.config.feedback_sounds:
            await self._play_sound("stop")

        if len(audio) < self.config.sample_rate * self.config.min_recording_duration:
            logger.info("Recording too short, ignoring")
            return

        # Transcribe
        text = await self._transcribe(audio)
        if not text:
            return

        logger.info(f"Transcribed: {text}")

        # Parse command
        command = self.parser.parse(text)
        logger.info(f"Command: {command}")

        # Send to gforge
        await self._send_command(command)

    async def _transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text"""
        if not self.model:
            logger.warning("Model not loaded, cannot transcribe")
            return ""

        # Save to temp file (faster-whisper needs a file)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            import wave
            with wave.open(f.name, 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.config.sample_rate)
                wf.writeframes((audio * 32767).astype(np.int16).tobytes())

            temp_path = f.name

        try:
            segments, _ = self.model.transcribe(temp_path, language="en")
            text = " ".join([s.text for s in segments])
            return text.strip()
        finally:
            Path(temp_path).unlink()

    async def _send_command(self, command: dict):
        """Send command to gforge via socket"""
        # Broadcast to all connected clients
        data = json.dumps(command).encode()
        # The Go client will connect to receive commands
        # For now, just log it
        logger.info(f"Would send to gforge: {command}")

    async def _socket_server(self):
        """Handle incoming socket connections"""
        loop = asyncio.get_event_loop()

        while self.running:
            try:
                client, _ = await loop.sock_accept(self.socket)
                asyncio.create_task(self._handle_client(client))
            except Exception as e:
                if self.running:
                    logger.error(f"Socket error: {e}")
                await asyncio.sleep(0.1)

    async def _handle_client(self, client: socket.socket):
        """Handle a client connection"""
        loop = asyncio.get_event_loop()
        client.setblocking(False)

        logger.info("Client connected")

        try:
            while self.running:
                # Read messages from client (e.g., control commands)
                try:
                    data = await asyncio.wait_for(
                        loop.sock_recv(client, 4096),
                        timeout=1.0
                    )
                    if not data:
                        break

                    msg = json.loads(data.decode())
                    await self._handle_control(msg, client)
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
        finally:
            client.close()
            logger.info("Client disconnected")

    async def _handle_control(self, msg: dict, client: socket.socket):
        """Handle control messages from gforge"""
        action = msg.get("action")

        if action == "start_recording":
            await self._start_recording()
            await self._send_to_client(client, {"status": "recording"})

        elif action == "stop_recording":
            await self._stop_recording()
            await self._send_to_client(client, {"status": "stopped"})

        elif action == "status":
            await self._send_to_client(client, {
                "status": "ok",
                "recording": self.recording_active,
                "model": self.config.model_size
            })

    async def _send_to_client(self, client: socket.socket, msg: dict):
        """Send message to client"""
        loop = asyncio.get_event_loop()
        data = json.dumps(msg).encode()
        await loop.sock_sendall(client, data)

    async def _play_sound(self, sound_type: str):
        """Play feedback sound"""
        # Simple beep using sounddevice
        try:
            duration = 0.1
            freq = 800 if sound_type == "start" else 400
            t = np.linspace(0, duration, int(self.config.sample_rate * duration))
            wave = np.sin(2 * np.pi * freq * t) * 0.3
            sd.play(wave, self.config.sample_rate)
        except Exception as e:
            logger.debug(f"Could not play sound: {e}")

    def _shutdown(self):
        """Shutdown the daemon"""
        logger.info("Shutting down...")
        self.running = False
        if self.socket:
            self.socket.close()
        if Path(self.config.socket_path).exists():
            Path(self.config.socket_path).unlink()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Goblin Forge Voice Daemon")
    parser.add_argument("--socket", default="/tmp/gforge-voice.sock",
                        help="Unix socket path")
    parser.add_argument("--model", default="tiny",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size")
    parser.add_argument("--device", default="auto",
                        choices=["cpu", "cuda", "auto"],
                        help="Compute device")
    parser.add_argument("--hotkey", default="KEY_SCROLLLOCK",
                        help="Hotkey for push-to-talk")
    parser.add_argument("--no-sounds", action="store_true",
                        help="Disable feedback sounds")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = Config(
        socket_path=args.socket,
        model_size=args.model,
        device=args.device,
        hotkey_key=args.hotkey,
        feedback_sounds=not args.no_sounds
    )

    daemon = VoiceDaemon(config)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
