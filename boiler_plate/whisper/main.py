import whisper
import sys
import torch
import argparse

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio using Whisper with timestamps.")
    parser.add_argument("--audio", type=str, default="audio.webm", help="Path to the audio file")
    parser.add_argument("--model", type=str, default="turbo", help="Whisper model to use (e.g., tiny, base, small, medium, large, turbo)")
    parser.add_argument("--language", type=str, default=None, help="Language code (e.g., en, fr, de, etc.)")
    parser.add_argument("--task", type=str, default="transcribe", choices=["transcribe", "translate"], help="Task: transcribe or translate")
    args = parser.parse_args()

    # Check for CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Load the specified model
    model = whisper.load_model(args.model, device=device)
    print(f"Model {args.model} loaded.")

    # Transcribe the audio file
    print(f"Transcribing: {args.audio}")
    result = model.transcribe(
        args.audio,
        language=args.language,
        task=args.task,
        verbose=True
    )

    # Print transcription with timestamps
    print("\nTranscription with timestamps:")
    for segment in result["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        print(f"[{start:.2f}s -> {end:.2f}s] {text}")

if __name__ == "__main__":
    main()
