from __future__ import annotations

import asyncio
import dataclasses
import websockets
import json
from dataclasses import dataclass
from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APITimeoutError,
    stt,
)
from livekit.agents.utils import AudioBuffer
from livekit.agents.vad import VAD
from livekit.agents.stt import StreamAdapter

@dataclass
class _STTOptions:
    language: str
    detect_language: bool
    model: str

class STT(stt.STT):
    def __init__(
        self,
        *,
        language: str = "en",
        model: str = "Systran/faster-distil-whisper-large-v3",
        websocket_url: str = "ws://172.16.101.49:8001/v1/audio/transcriptions",
        vad: VAD,
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True)
        )

        self._opts = _STTOptions(
            language=language,
            detect_language=False,
            model=model,
        )
        self.websocket_url = f"{websocket_url}?model={model}&language={language}"
        self._vad = vad

    def update_options(
        self,
        *,
        model: str | None = None,
        language: str | None = None,
    ) -> None:
        if model:
            self._opts.model = model
        if language:
            self._opts.language = language

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        try:
            config = dataclasses.replace(self._opts)
            if language:
                config.language = language

            data = rtc.combine_audio_frames(buffer).to_wav_bytes()
            
            async with websockets.connect(self.websocket_url) as ws:
                await ws.send(data)  # Send binary WAV data
                response = await ws.recv()  # Receive transcription response
                response_data = json.loads(response)

            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        text=response_data.get("text", ""),
                        language=response_data.get("language", config.language),
                    )
                ],
            )
        
        except asyncio.TimeoutError:
            raise APITimeoutError()
        except websockets.exceptions.WebSocketException as e:
            raise APIConnectionError(f"WebSocket error: {str(e)}")
        except Exception as e:
            raise APIConnectionError() from e

    def stream(
        self,
        *,
        language: str | None = None,
        conn_options: APIConnectOptions = APIConnectOptions(),
    ) -> stt.RecognizeStream:
        """Enable streaming STT support using the WebSocket-based STT service."""
        return StreamAdapter(stt=self, vad=self._vad).stream(
            language=language, conn_options=conn_options
        )
