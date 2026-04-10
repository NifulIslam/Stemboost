import sys
import torch
import librosa
import numpy as np
import soundfile as sf
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

MODEL_ID = "openai/whisper-large-v3"
DEVICE   = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE    = torch.float16 if torch.cuda.is_available() else torch.float32


def load_model(model_id: str = MODEL_ID):
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=DTYPE,
        low_cpu_mem_usage=True,
        use_safetensors=True,
    ).to(DEVICE)

    processor = AutoProcessor.from_pretrained(model_id)

    return pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=DTYPE,
        device=DEVICE,
        return_timestamps=True,
    )


def transcribe_file(audio_path: str, asr_pipe, language: str = None) -> dict:
    generate_kwargs = {"language": language} if language else {}
    result = asr_pipe(audio_path, generate_kwargs=generate_kwargs)

    return {
        "text":     result.get("text", "").strip(),
        "chunks":   result.get("chunks", []),
        "language": language or "auto-detected",
    }


def transcribe_array(audio_array: np.ndarray, sample_rate: int, asr_pipe) -> str:
    if sample_rate != 16_000:
        audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16_000)

    result = asr_pipe({"array": audio_array, "sampling_rate": 16_000})
    return result.get("text", "").strip()


def create_test_audio(path: str = "/tmp/test_audio.wav") -> str:
    silence = np.zeros(16_000, dtype=np.float32)
    sf.write(path, silence, 16_000)
    return path


def print_result(output: dict) -> None:
    print(f"\nLanguage : {output['language']}")
    print(f"Text     : {output['text'] or '(silence / no speech detected)'}")

    if output["chunks"]:
        print("\nTimestamped chunks:")
        for chunk in output["chunks"]:
            ts = chunk.get("timestamp", ("?", "?"))
            print(f"  [{ts[0]:.2f}s -> {ts[1]:.2f}s]  {chunk['text']}")


if __name__ == "__main__":
    audio_file = sys.argv[1] if len(sys.argv) > 1 else create_test_audio()

    asr_pipe = load_model()
    output   = transcribe_file(audio_file, asr_pipe)

    print_result(output)


