from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
from pathlib import Path
import torch

model_id = "microsoft/git-base-coco"  

print("Loading model...")
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

model.eval()
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")
model = model.to(device)


def generate_caption(image_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=100,
            num_beams=4,
            repetition_penalty=1.5,
        )

    caption = processor.decode(output_ids[0], skip_special_tokens=True)
    return caption.strip()


def save_caption(image_path: str, caption: str) -> Path:
    image_path = Path(image_path).resolve()
    metadata_dir = image_path.parent.parent / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    caption_file = metadata_dir / (image_path.stem + ".txt")
    caption_file.write_text(caption, encoding="utf-8")
    return caption_file


def caption_and_save(image_path: str) -> tuple[str, Path]:
    print(f"Processing: {image_path}")
    caption = generate_caption(image_path)
    saved_to = save_caption(image_path, caption)
    print(f"Caption : {caption}")
    print(f"Saved to: {saved_to}")
    return caption, saved_to


caption_and_save("image-to-text/sample image/bore_model.jpg")