import threading
import tkinter as tk
from typing import Optional, Callable, Any, Tuple

from pynput import keyboard
import pyautogui
import pyperclip

from modules.status_manager import StatusConfig

class UIFeedback:
    pyautogui_lock = threading.Lock()

    def __init__(self):
        # Create the floating window
        self.root = tk.Tk()
        self.root.withdraw()  # Hide initially?
        self.indicator = tk.Toplevel(self.root)
        self.indicator.withdraw()

        # Configure the indicator window
        self.indicator.overrideredirect(True)  # Remove window decorations
        self.indicator.attributes('-topmost', True)  # Keep on top
        self.indicator.configure(bg='red')

        # Create main frame
        self.frame = tk.Frame(self.indicator, bg='red')
        self.frame.pack(expand=True, fill='both', padx=2, pady=2)

        # Create label with click binding
        self.label = tk.Label(self.frame, text="🎤 Recording (click to cancel)",
                            fg='white', bg='red', padx=10, pady=5,
                            cursor="hand2")  # Change cursor to hand on hover
        self.label.pack()

        # Create audio level indicator (initially hidden)
        self.level_canvas = tk.Canvas(self.frame, height=4, bg='darkred',
                                    highlightthickness=0)
        self.level_canvas.pack(fill='x', padx=4, pady=(0, 4))
        self.level_bar = self.level_canvas.create_rectangle(0, 0, 0, 4,
                                                          fill='white', width=0)

        # Add pulsing state variables
        self.pulsing = False
        self.RECORDING_COLORS = ['red', 'darkred']
        self.pulse_colors = self.RECORDING_COLORS
        self.current_color = 0

        # Add click callback placeholder
        self.on_click_callback = None

        # Add retry callback placeholder
        self.on_retry_callback: Optional[Callable[[], None]] = None
        self.retry_available = False

        # Bind click events
        self.label.bind('<Button-1>', self._handle_click)
        self.indicator.bind('<Button-1>', self._handle_click)
        self.level_canvas.bind('<Button-1>', self._handle_click)

        # Position window in top-right corner
        screen_width = self.root.winfo_screenwidth()
        self.indicator.geometry(f'+{screen_width-150}+10')

        # Add warning state variables
        self.warning_color = '#FFA500'  # Orange warning color
        self.warning_timer: Optional[str] = None

        # Update label text color to be more visible on warning background
        self.label.configure(fg='black')  # Will be dynamically changed based on state

    def update_audio_level(self, level: float) -> None:
        """Update the audio level indicator (level should be between 0.0 and 1.0)"""
        if self.pulsing:  # Only update when recording
            width = self.level_canvas.winfo_width()
            bar_width = int(width * min(1.0, max(0.0, level)))
            self.level_canvas.coords(self.level_bar, 0, 0, bar_width, 4)

    def _pulse(self) -> None:
        if self.pulsing:
            self.current_color = (self.current_color + 1) % 2
            color = self.pulse_colors[self.current_color]
            self.indicator.configure(bg=color)
            self.frame.configure(bg=color)
            self.label.configure(bg=color)
            self.indicator.after(500, self._pulse)  # Pulse every 500ms

    def start_listening_animation(self) -> None:
        """Start the recording animation"""
        # Cancel any existing warning state
        if self.warning_timer:
            self.indicator.after_cancel(self.warning_timer)
            self.warning_timer = None

        self.pulse_colors = self.RECORDING_COLORS
        self.label.configure(
            text="🎤 Recording (click to cancel)",
            fg='white'
        )
        self.level_canvas.pack(fill='x', padx=4, pady=(0, 4))
        self.indicator.deiconify()
        self.pulsing = True
        self._pulse()

    def stop_listening_animation(self) -> None:
        """Stop the recording animation"""
        self.pulsing = False
        # Only hide if no warning is active
        if not self.warning_timer:
            self.indicator.withdraw()
        # Reset colors to recording state
        self.current_color = 0
        self.indicator.configure(bg=self.RECORDING_COLORS[0])
        self.frame.configure(bg=self.RECORDING_COLORS[0])
        self.label.configure(bg=self.RECORDING_COLORS[0])
        # Reset audio level
        self.level_canvas.coords(self.level_bar, 0, 0, 0, 4)

    def _handle_click(self, event: tk.Event) -> None:
        if self.retry_available and self.on_retry_callback:
            self.retry_available = False
            self.on_retry_callback()
        elif self.on_click_callback:
            self.on_click_callback()

    def set_click_callback(self, callback: Callable[[], None]) -> None:
        """Set the function to be called when the indicator is clicked"""
        self.on_click_callback = callback

    def set_retry_callback(self, callback: Callable[[], None]) -> None:
        """Set the function to be called when retry is clicked"""
        self.on_retry_callback = callback

    def insert_text(self, text: str) -> None:
        """Insert text at the current cursor position using clipboard while preserving original clipboard content"""
        try:
            with self.pyautogui_lock:
                # Save original clipboard content
                original_clipboard = pyperclip.paste()

                # Copy new text and paste it
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')

                # Restore original clipboard content after a small delay (non-blocking)
                self.root.after(100, lambda: pyperclip.copy(original_clipboard))
        except Exception as e:
            print(f"UIFeedback: Error during text insertion: {str(e)}")

    def show_warning(self, message: str, duration_ms: int = 5000) -> None:
        """Show a warning message in the indicator for a specified duration"""
        # Cancel any existing warning timer
        if self.warning_timer:
            self.indicator.after_cancel(self.warning_timer)

        # Update appearance for warning state
        self.indicator.deiconify()
        self.indicator.configure(bg=self.warning_color)
        self.frame.configure(bg=self.warning_color)
        self.label.configure(
            bg=self.warning_color,
            fg='black',  # Dark text for warning state
            text=message
        )

        # Hide the level indicator during warning
        self.level_canvas.pack_forget()

        # Schedule auto-dismiss
        self.warning_timer = self.indicator.after(
            duration_ms,
            self._reset_and_hide
        )

    def show_error_with_retry(self, message: str, duration_ms: int = 7000) -> None:
        """Show error message with retry option"""
        # Cancel any existing warning timer
        if self.warning_timer:
            self.indicator.after_cancel(self.warning_timer)

        self.retry_available = True

        # Update appearance for error state
        self.indicator.deiconify()
        self.indicator.configure(bg=self.warning_color)
        self.frame.configure(bg=self.warning_color)
        self.label.configure(
            bg=self.warning_color,
            fg='black',
            text=f"{message}\n🔄 Click to retry"
        )

        # Hide the level indicator during warning
        self.level_canvas.pack_forget()

        # Schedule auto-dismiss
        self.warning_timer = self.indicator.after(
            duration_ms,
            self._reset_and_hide
        )

    def _reset_and_hide(self) -> None:
        """Reset UI state and hide the indicator"""
        self.warning_timer = None
        self.retry_available = False
        self.level_canvas.pack(fill='x', padx=4, pady=(0, 4))  # Restore level indicator
        self.indicator.withdraw()
        # Reset to recording state colors
        self.indicator.configure(bg=self.RECORDING_COLORS[0])
        self.frame.configure(bg=self.RECORDING_COLORS[0])
        self.label.configure(
            bg=self.RECORDING_COLORS[0],
            fg='white'  # Reset to white text for recording state
        )

    def update_status(self, config: StatusConfig, error_message: Optional[str] = None) -> None:
        """Update UI appearance based on status configuration"""
        # Update colors and text
        text = error_message if error_message else config.ui_text

        self.indicator.configure(bg=config.ui_color)
        self.frame.configure(bg=config.ui_color)
        self.label.configure(
            bg=config.ui_color,
            fg=config.ui_fg_color,
            text=text
        )

        # Handle visibility and animation
        if config.pulse:
            self.pulse_colors = [config.ui_color, self._darken_color(config.ui_color)]
            self.indicator.deiconify()
            self.pulsing = True
            self._pulse()
        else:
            self.pulsing = False
            if error_message:
                self.indicator.deiconify()
                # Auto-hide after 5 seconds for errors
                if self.warning_timer:
                    self.indicator.after_cancel(self.warning_timer)
                self.warning_timer = self.indicator.after(5000, self._reset_and_hide)
            else:
                self.indicator.withdraw()

    def _darken_color(self, color: str) -> str:
        """Create a darker version of the given color for pulsing effect"""
        try:
            # Handle invalid or empty color values
            if not color or len(color) != 7 or not color.startswith('#'):
                return '#000000'  # Default to black if invalid color

            # Convert hex to RGB, darken, convert back to hex
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            factor = 0.7  # Darken by 30%
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)

            return f'#{r:02x}{g:02x}{b:02x}'
        except ValueError:
            print(f"Warning: Invalid color format: {color}")
            return '#000000'  # Fallback color

    def cleanup(self) -> None:
        """Ensure proper cleanup of UI resources"""
        if self.warning_timer:
            self.indicator.after_cancel(self.warning_timer)
        self.pulsing = False
        self.indicator.withdraw()
        self.root.quit()


if __name__ == "__main__":
    import time

    class UITester:
        def __init__(self) -> None:
            print("Starting UI feedback test...")
            print("Press Caps Lock to toggle recording indicator")
            print("Press Ctrl+C to exit")

            self.ui = UIFeedback()
            self.recording = False
            self.listener = None

        def on_press(self, key: keyboard.Key) -> None:
            if key == keyboard.Key.caps_lock:
                self.recording = not self.recording
                if self.recording:
                    print("Recording started")
                    self.ui.start_listening_animation()
                else:
                    print("Recording stopped")
                    self.ui.stop_listening_animation()

        def run(self) -> None:
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()

            try:
                self.ui.root.mainloop()
            except KeyboardInterrupt:
                self.cleanup()

        def cleanup(self) -> None:
            if self.listener:
                self.listener.stop()
            if self.recording:
                self.ui.stop_listening_animation()
            self.ui.root.destroy()
            print("\nTest ended")

    # Create and run the tester
    tester = UITester()
    tester.run()