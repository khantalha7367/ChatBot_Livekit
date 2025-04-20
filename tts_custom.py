import httpx
import urllib.parse
import uuid
import asyncio
from livekit.agents import (
    tts,
    APIConnectionError,
    APIConnectOptions,
    APITimeoutError,
    APIStatusError,
    DEFAULT_API_CONNECT_OPTIONS,
)
from livekit.agents.utils import audio
 
class LocalTTS(tts.TTS):
    """
    Custom TTS that streams audio from a locally hosted endpoint.
    """
 
    def __init__(
        self,
        base_url: str = "http://172.16.101.49:5002/api/stream",
        speaker_id: str = "Rosemary Okafor",
        language_id: str = "en",
        sample_rate: int = 22050,
        num_channels: int = 1
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=sample_rate,
            num_channels=num_channels,
        )
        self._base_url = base_url
        self._speaker_id = speaker_id
        self._language_id = language_id
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # or specify all four: connect=, read=, write=, pool=
            follow_redirects=True,
        )
 
    # ---------------------------------------------------------
    # ADDED stream() method here
    # ---------------------------------------------------------
    def stream(
        self,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "LocalTTSStream":
        """
        Overriding TTS.stream() so the pipeline can do streaming TTS.
        We return a ChunkedStream just like `synthesize(...)` does.
        The pipeline will call `tts_stream.set_text(...)` to set the text.
        """
        if not self.capabilities.streaming:
            raise NotImplementedError(
                "streaming is not supported by this TTS, please use a different TTS or use a StreamAdapter"
            )
        # Return a chunked stream with an empty `input_text` for now;
        # The pipeline typically sets the text after creating the stream.
        return LocalTTSStream(
            tts=self,
            input_text="",  # will be set later
            conn_options=conn_options,
            base_url=self._base_url,
            speaker_id=self._speaker_id,
            language_id=self._language_id,
            sample_rate=self._sample_rate,
            num_channels=self._num_channels,
        )
 
    # ---------------------------------------------------------
    # If your pipeline instead calls tts.synthesize(text=...)
    # for non-streaming usage, keep this function, too.
    # ---------------------------------------------------------
    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "LocalTTSStream":
        return LocalTTSStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            base_url=self._base_url,
            speaker_id=self._speaker_id,
            language_id=self._language_id,
            sample_rate=self._sample_rate,
            num_channels=self._num_channels,
        )
 
 
class LocalTTSStream(tts.ChunkedStream):
    """
    A chunked streaming generator that connects to the local TTS endpoint.
    """
 
    def __init__(
        self,
        tts: LocalTTS,
        input_text: str,
        conn_options: APIConnectOptions,
        base_url: str,
        speaker_id: str,
        language_id: str,
        sample_rate: int,
        num_channels: int
    ):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._base_url = base_url
        self._speaker_id = speaker_id
        self._language_id = language_id
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._client = tts._client
 
    async def _run(self):
        request_id = uuid.uuid4().hex[:8]
 
        # The pipeline calls tts_stream.set_text(...) if your text isn't set yet.
        # So we read self.input_text here:
        encoded_text = urllib.parse.quote_plus(self.input_text)
        url = (
            f"{self._base_url}"
            f"?text={encoded_text}"
            f"&speaker_id={urllib.parse.quote_plus(self._speaker_id)}"
            f"&style_wav="
            f"&language_id={self._language_id}"
        )
 
        try:
            async with self._client.stream("GET", url) as resp:
                resp.raise_for_status()
 
                audio_bstream = audio.AudioByteStream(
                    sample_rate=self._sample_rate,
                    num_channels=self._num_channels,
                )
                async for chunk in resp.aiter_bytes():
                    for frame in audio_bstream.write(chunk):
                        self._event_ch.send_nowait(
                            tts.SynthesizedAudio(frame=frame, request_id=request_id)
                        )
                for frame in audio_bstream.flush():
                    self._event_ch.send_nowait(
                        tts.SynthesizedAudio(frame=frame, request_id=request_id)
                    )
 
        except httpx.ReadTimeout:
            raise APITimeoutError("Local TTS read timed out.")
        except httpx.HTTPStatusError as e:
            raise APIStatusError(
                f"Local TTS returned error: {e.response.status_code} {e.response.text}",
                status_code=e.response.status_code,
                body=e.response.text,
            )
        except Exception as e:
            raise APIConnectionError(f"Local TTS error: {str(e)}") from e