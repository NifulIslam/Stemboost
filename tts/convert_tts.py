import sys
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
from datasets import load_dataset
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan

MODEL_ID       = "microsoft/speecht5_tts"
VOCODER_ID     = "microsoft/speecht5_hifigan"
DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"
DEFAULT_OUTPUT = "output_speech.wav"
SAMPLE_RATE    = 16_000


def load_model(model_id: str = MODEL_ID, vocoder_id: str = VOCODER_ID):
    processor = SpeechT5Processor.from_pretrained(model_id)
    model     = SpeechT5ForTextToSpeech.from_pretrained(model_id).to(DEVICE)
    vocoder   = SpeechT5HifiGan.from_pretrained(vocoder_id).to(DEVICE)
    embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")

    return processor, model, vocoder, embeddings_dataset


def get_speaker_embedding(embeddings_dataset, speaker_index: int = 7306) -> torch.Tensor:
    return torch.tensor(
        embeddings_dataset[speaker_index]["xvector"]
    ).unsqueeze(0).to(DEVICE)


def synthesize(
    text: str,
    processor,
    model,
    vocoder,
    speaker_embeddings: torch.Tensor,
    output_path: str = DEFAULT_OUTPUT,
) -> np.ndarray:
    inputs = processor(text=text, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        speech = model.generate_speech(
            inputs["input_ids"],
            speaker_embeddings,
            vocoder=vocoder,
        )

    audio_np = speech.cpu().numpy()
    sf.write(output_path, audio_np, SAMPLE_RATE)

    return audio_np


def print_result(text: str, audio: np.ndarray, output_path: str) -> None:
    print(f"\nCharacters  : {len(text)}")
    print(f"Audio length: {len(audio) / SAMPLE_RATE:.2f}s")
    print(f"Output file : {Path(output_path).resolve()}")


def main():
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello! This is a text-to-speech demo using a Hugging Face model."

    processor, model, vocoder, emb_dataset = load_model()
    speaker_emb = get_speaker_embedding(emb_dataset)
    audio = synthesize(text, processor, model, vocoder, speaker_emb, DEFAULT_OUTPUT)

    print_result(text, audio, DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()