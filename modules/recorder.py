import threading
from typing import Optional, Callable, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf

# NOTE: Optimized settings for speech recording
# - 16kHz sample rate is optimal for STT, using 22.05kHz for safety margin
# - 16-bit depth is standard for speech
# - Mono channel as stereo provides no benefit
# - WAV format ensures compatibility and quality
# NOTE: Ends up being ~2.6 megabytes for every 60 seconds with these settings.

# CONSTANTS: Audio analysis thresholds
# RMS threshold below which audio is considered silence
# (-30 dB = 0.0316, -40 dB = 0.01, -50 dB = 0.003)
SILENCE_THRESHOLD = 0.01
# Minimum duration in seconds for valid recordings
MIN_DURATION = 2.0

class AudioRecorder:
    # Controls how smooth/reactive the audio level indicator bar appears in the UI
    # (0.0 to 1.0) Higher = more responsive but jerky, Lower = more smooth, but slower
    # 0.2 provides a good balance between smoothness and responsiveness
    SMOOTHING_FACTOR = 0.2

    def __init__(self, filename: str = 'temp_audio.wav', level_callback: Optional[Callable[[float], None]] = None) -> None:
        self.filename = filename
        self.recording = False
        self.thread: Optional[threading.Thread] = None
        self.level_callback = level_callback
        self.smoothed_level: float = 0.0
        self.stream: Optional[sd.InputStream] = None
        self.file: Optional[sf.SoundFile] = None
        self._lock: threading.Lock = threading.Lock()
        self.audio_data: list[np.ndarray] = []  # Store audio chunks for analysis

    def _calculate_level(self, indata: np.ndarray) -> float:
        """Calculate audio level from input data"""
        # Get the RMS value from the audio data
        rms = np.sqrt(np.mean(np.square(indata)))
        # Convert to a log scale and normalize
        # -60 dB to 0 dB range mapped to 0.0 to 1.0
        db = 20 * np.log10(max(1e-10, rms))  # Avoid log(0)
        normalized = (db + 60) / 60  # Map -60..0 to 0..1
        current_level = max(0.0, min(1.0, normalized))  # Clamp to 0..1

        # Apply smoothing
        self.smoothed_level = (self.SMOOTHING_FACTOR * current_level) + ((1 - self.SMOOTHING_FACTOR) * self.smoothed_level)
        return self.smoothed_level

    def analyze_recording(self) -> Tuple[bool, str]:
        """Analyze the recorded audio file for silence and duration.

        Returns:
            Tuple[bool, str]: (is_valid, reason_if_invalid)
        """
        try:
            with sf.SoundFile(self.filename) as audio_file:
                # Check duration
                duration = len(audio_file) / audio_file.samplerate
                if duration < MIN_DURATION:
                    return False, f"Recording too short ({duration:.1f}s < {MIN_DURATION}s)"

                # Read the entire file
                audio_data = audio_file.read()

                # Calculate RMS value
                rms = np.sqrt(np.mean(np.square(audio_data)))

                # Check if mostly silence
                if rms < SILENCE_THRESHOLD:
                    return False, "Recording contains mostly silence"

                return True, ""

        except Exception as e:
            return False, f"Error analyzing audio: {str(e)}"

    def _record(self) -> None:
        def audio_callback(indata: np.ndarray,
                         frames: int,
                         time: float,
                         status: int) -> None:
            with self._lock:
                if not self.recording or self.file is None:
                    return

                if self.level_callback:
                    level = self._calculate_level(indata)
                    self.level_callback(level)
                try:
                    self.file.write(indata.copy())
                except Exception as e:
                    print(f"Audio callback error: {e}")

        try:
            self.file = sf.SoundFile(self.filename, mode='w', samplerate=22050,
                                   channels=1, subtype='PCM_16', format='WAV')
            self.stream = sd.InputStream(samplerate=22050, channels=1,
                                       callback=audio_callback)
            with self.file, self.stream:
                while self.recording:
                    sd.sleep(100)
        finally:
            with self._lock:
                if self.stream is not None:
                    self.stream.close()
                    self.stream = None
                if self.file is not None:
                    self.file.close()
                    self.file = None

    def start(self) -> None:
        self.recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()

    def stop(self) -> None:
        """Stop recording with timeout to prevent hanging"""
        with self._lock:
            self.recording = False

        if self.thread:
            # Add timeout to thread.join() to prevent hanging
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                print("Warning: Recording thread did not stop cleanly")
                # Force cleanup
                with self._lock:
                    if self.stream is not None:
                        try:
                            self.stream.close()
                        except:
                            pass
                        self.stream = None
                    if self.file is not None:
                        try:
                            self.file.close()
                        except:
                            pass
                        self.file = None