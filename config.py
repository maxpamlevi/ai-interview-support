import os
from dotenv import load_dotenv

load_dotenv()

# Audio Settings
SAMPLE_RATE = 48000  # Increased for better system audio compatibility
BLOCK_SIZE = 1536    # Divisible by 3 for 48k -> 16k decimation
CHANNELS = 1

# VAD Settings
VAD_THRESHOLD = 0.5
SILENCE_DURATION_MS = 700  # Reduced to make it more responsive
SILENCE_DURATION_MS = 700  # Reduced to make it more responsive
SPEECH_PAD_MS = 300       # Padding around speech
SPEECH_PAD_MS = 300       # Padding around speech
MAX_SPEECH_DURATION_S = 30 # Max duration to force processing if no silence found
MIN_SPEECH_PROB = 0.3      # Minimum probability to consider a chunk as speech for filtering

# Configuration settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


