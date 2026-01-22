try:
    import google.generativeai
    import sounddevice
    import numpy
    import torch
    import PyQt6
    print("Dependencies OK")
except ImportError as e:
    print(f"Missing dependency: {e}")
