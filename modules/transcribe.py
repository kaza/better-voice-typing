import os
from dotenv import load_dotenv
from openai import OpenAI

# OpenAI Speech to text docs: https://platform.openai.com/docs/guides/speech-to-text
# ⚠️ IMPORTANT: OpenAI Audio API file uploads are currently limited to 25 MB

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def transcribe_audio(filename: str, language: str = "en") -> str:
    """
    Transcribe audio file using OpenAI's Whisper model.
    
    Args:
        filename (str): Path to the audio file
        language (str): Language code (e.g., "en" for English, "es" for Spanish)
                       See OpenAI docs for supported languages
    
    Returns:
        str: Transcribed text
    """
    with open(filename, 'rb') as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language
        )
    return response.text