import threading
from typing import Optional, Callable, Tuple, Any
import time

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
MIN_DURATION = 1.0
# Time of continuous silence (in seconds) before auto-stopping
DEFAULT_SILENCE_TIMEOUT = 4.0

class AudioRecorder:
    # Controls how smooth/reactive the audio level indicator bar appears in the UI
    # (0.0 to 1.0) Higher = more responsive but jerky, Lower = more smooth, but slower
    # 0.2 provides a good balance between smoothness and responsiveness
    SMOOTHING_FACTOR = 0.2

    def __init__(self, filename: str = 'temp_audio.wav',
                 level_callback: Optional[Callable[[float], None]] = None,
                 silence_timeout: Optional[float] = None) -> None:
        self.filename = filename
        self.recording = False
        self.thread: Optional[threading.Thread] = None
        self.level_callback = level_callback
        self.smoothed_level: float = 0.0
        self.stream: Optional[sd.InputStream] = None
        self.file: Optional[sf.SoundFile] = None
        self._lock: threading.Lock = threading.Lock()
        self.audio_data: list[np.ndarray] = []  # Store audio chunks for analysis
        self.silence_start: Optional[float] = None
        self.silence_timeout = silence_timeout
        self.auto_stopped = False
        self.recording_start_time: Optional[float] = None
        self.INITIAL_CHECK_DURATION = 4.0  # Only check first n seconds for silence
        self.initial_sound_detected = False  # Track if we've detected any sound

    def _calculate_level(self, indata: np.ndarray) -> float:
        """Calculate audio level from input data"""
        rms = np.sqrt(np.mean(np.square(indata)))

        # Convert to dB for level display
        db = 20 * np.log10(max(1e-10, rms))
        normalized = (db + 60) / 60
        current_level = max(0.0, min(1.0, normalized))

        # Only check for silence during the initial period
        if (self.silence_timeout is not None and
            self.recording_start_time is not None):

            elapsed_time = time.time() - self.recording_start_time

            # Only perform silence detection during initial period and before any sound is detected
            if elapsed_time <= self.INITIAL_CHECK_DURATION and not self.initial_sound_detected:
                if rms < SILENCE_THRESHOLD:
                    if self.silence_start is None:
                        self.silence_start = time.time()
                    elif time.time() - self.silence_start >= self.silence_timeout:
                        print(f"Auto-stopping due to {self.silence_timeout}s of initial silence")
                        self.auto_stopped = True
                        self.recording = False
                        return 0.0
                else:
                    # We've detected sound, stop checking for silence
                    self.initial_sound_detected = True
                    self.silence_start = None

        # Apply smoothing for UI feedback
        self.smoothed_level = (self.SMOOTHING_FACTOR * current_level) + \
                              ((1 - self.SMOOTHING_FACTOR) * self.smoothed_level)

        if self.level_callback:
            self.level_callback(self.smoothed_level)

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
        """Record audio in a separate thread"""
        def audio_callback(indata: np.ndarray,
                         frames: int,
                         time_info: Any,
                         status: int) -> None:
            if status:
                print(f'Audio callback status: {status}')

            with self._lock:
                if not self.recording or self.file is None:
                    return

                if self.level_callback:
                    level = self._calculate_level(indata)
                    self.level_callback(level)

                    # If auto-stopped, stop the stream
                    if self.auto_stopped:
                        self.recording = False
                        raise sd.CallbackStop()

                # Only write audio data if not auto-stopped
                if not self.auto_stopped and self.file is not None:
                    try:
                        self.file.write(indata.copy())
                    except Exception as e:
                        print(f"Audio callback error: {e}")
                        self.recording = False
                        raise sd.CallbackStop()

        try:
            with sf.SoundFile(self.filename, mode='w',
                            samplerate=22050,
                            channels=1,
                            subtype='PCM_16',
                            format='WAV') as self.file:
                with sd.InputStream(samplerate=22050,
                                  channels=1,
                                  callback=audio_callback) as self.stream:
                    while self.recording:
                        sd.sleep(100)
        except Exception as e:
            print(f"Recording error: {e}")
            self.auto_stopped = True
        finally:
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

    def start(self) -> None:
        """Start recording and reset silence detection"""
        self.auto_stopped = False
        self.silence_start = None
        self.initial_sound_detected = False
        self.recording_start_time = time.time()
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

    def was_auto_stopped(self) -> bool:
        """Check if recording was automatically stopped due to silence"""
        return self.auto_stopped