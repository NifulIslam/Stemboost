"""
STEMboost Utilities
- generate_image_caption: uses microsoft/git-base-coco to describe uploaded images
"""
import logging

logger = logging.getLogger(__name__)


def generate_image_caption(image_path: str) -> str:
    """
    Generate a text description for a chapter image using microsoft/git-base-coco.
    Falls back to a generic description if the model is not available.

    Adapted from image-to-text/save_image_caption.py
    """
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForCausalLM
        from PIL import Image

        model_id = "microsoft/git-base-coco"
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id)
        model.eval()

        # Use MPS on Apple Silicon, CUDA on GPU, else CPU
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        model = model.to(device)

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

    except ImportError:
        logger.warning(
            "transformers/torch not installed — image captioning unavailable. "
            "Install with: pip install transformers torch Pillow"
        )
        return "Image uploaded. Automatic description requires the transformers library."
    except Exception as exc:
        logger.error("Image captioning failed: %s", exc)
        return "Image description could not be generated automatically."
