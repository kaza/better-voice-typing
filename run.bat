@echo off
echo Starting Voice Typing Assistant...

REM Activate virtual environment
call .venv\Scripts\activate

REM Run the voice typing application with python instead of pythonw to see console output
python voice_typing.pyw

REM Note: Using 'python' instead of 'pythonw' to show console output 