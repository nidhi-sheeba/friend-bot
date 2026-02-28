# voice.py
import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# OpenAI client — used specifically for Whisper transcription
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def transcribe_voice(file) -> str:
    """
    Downloads a Telegram voice file and transcribes it using Whisper.
    
    `file` is a Telegram File object — it has a .download_to_drive() method
    that saves the audio to a local path.
    
    Returns the transcribed text as a string.
    """

    # tempfile.NamedTemporaryFile creates a temporary file that auto-deletes
    # when we're done. suffix=".ogg" because Telegram voice messages are
    # in OGG format (a compressed audio format). delete=False means we
    # control when it gets deleted — needed because Whisper needs to
    # open it by filename.
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name  # save the path before closing

    # Download the audio file from Telegram's servers to our temp file
    await file.download_to_drive(tmp_path)

    try:
        # Open the downloaded file in binary read mode ("rb")
        # and send it to Whisper
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",   # Whisper's model name in the API
                file=audio_file,
                language="en"        # specify language for better accuracy
                                     # remove this line if you speak multiple languages
            )

        # transcript.text is the plain string of what was said
        return transcript.text

    finally:
        # Always delete the temp file whether transcription succeeded or failed
        # finally block runs even if an exception was raised
        os.unlink(tmp_path)