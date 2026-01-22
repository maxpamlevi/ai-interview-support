import google.generativeai as genai
import numpy as np
import tempfile
import os
import scipy.io.wavfile as wav
import config

class GeminiClient:
    def __init__(self, api_key):
        if not api_key or api_key == "YOUR_API_KEY":
            print("Warning: valid API key not provided.")
        
        genai.configure(api_key=api_key)
        # Using gemini-2.0-flash-exp as it is the latest fast model. 
        # User attempted '2.5' which doesn't exist.
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except:
            print("2.0 Flash not found, falling back to 1.5 Flash")
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
        self.chat = self.model.start_chat(history=[
            {"role": "user", "parts": ["You are a professional interview assistant. "
                                       "I will send you audio clips of the interviewer. "
                                       "Please listen to the question or statement and provide a concise, "
                                       "professional, and insightful suggestion for how I should respond. "
                                       "Keep your answer short (bullet points if needed) so I can read it quickly."]}
        ])

    def generate_suggestion(self, audio_data, language="English"):
        try:
            # Normalize Audio
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.9

            # Save audio to temp wav file
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Ensure debug directory exists
            debug_dir = "debug_audio"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            # Timestamp for filename
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{debug_dir}/recording_{timestamp}.wav"
            
            # Write directly to the debug file to keep it
            wav.write(filename, config.SAMPLE_RATE, audio_int16)
            print(f"Saved debug audio to {filename}")

            print(f"Sending audio to Gemini (Language: {language})...")
            
            sample_file = genai.upload_file(path=filename, display_name="Interview Audio")
            
            prompt = (f"You are a professional interview assistant. The user is speaking {language}. "
                      "Listen to the audio (interviewer question/statement) and provide a concise, "
                      f"professional suggestion for a response in {language}. "
                      "Keep your answer short/bullet points.")

            # We use a fresh chat or just generate content for single turn?
            # Using generate_content for statelessness might be better if we change system prompts dynamically
            # But the history is useful. 
            # Let's send the message to the chat.
            
            # Note: The system instruction was set in init. We can override or just append to user prompt.
            # Appending to user prompt is effective.
            
            
            response = self.chat.send_message([sample_file, prompt])
            
            # Cleanup (optional: usually we don't delete debug files immediately if user wants to see them)
            # os.remove(filename) 
            
            return response.text
            
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return f"Error: {e}"
