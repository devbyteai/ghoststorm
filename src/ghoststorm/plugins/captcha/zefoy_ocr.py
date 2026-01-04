"""Zefoy-specific OCR captcha solver with fallback options.

Uses multiple OCR methods:
1. Tesseract (primary) - fast and good for clean captchas
2. EasyOCR (fallback) - better for complex text
3. Multiple preprocessing strategies
"""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ZefoyOCRSolver:
    """OCR-based captcha solver optimized for Zefoy.

    Uses Tesseract as primary, EasyOCR as fallback.
    Tries multiple preprocessing strategies.
    """

    def __init__(self) -> None:
        self._tesseract_available = False
        self._easyocr_available = False
        self._pil_available = False
        self._easyocr_reader = None
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check available OCR dependencies."""
        try:
            import pytesseract
            self._tesseract_available = True
        except ImportError:
            logger.warning("pytesseract not installed. Install with: pip install pytesseract")

        try:
            import easyocr
            self._easyocr_available = True
        except ImportError:
            logger.debug("easyocr not installed. Install with: pip install easyocr")

        try:
            from PIL import Image
            self._pil_available = True
        except ImportError:
            logger.warning("Pillow not installed. Install with: pip install Pillow")

    def solve(self, image_bytes: bytes) -> str | None:
        """Solve captcha from image bytes (sync version).

        Tries multiple OCR methods and preprocessing strategies.

        Args:
            image_bytes: Raw image bytes (PNG/JPEG)

        Returns:
            Captcha solution string or None if failed
        """
        if not self._pil_available:
            logger.error("Pillow not available")
            return None

        # Strategy 1: Tesseract with default preprocessing
        if self._tesseract_available:
            solution = self._try_tesseract(image_bytes, preprocess="default")
            if solution:
                logger.info(f"[ZEFOY_OCR] Tesseract solved: {solution}")
                return solution

        # Strategy 2: Tesseract with inverted image
        if self._tesseract_available:
            solution = self._try_tesseract(image_bytes, preprocess="inverted")
            if solution:
                logger.info(f"[ZEFOY_OCR] Tesseract (inverted) solved: {solution}")
                return solution

        # Strategy 3: Tesseract with high contrast
        if self._tesseract_available:
            solution = self._try_tesseract(image_bytes, preprocess="high_contrast")
            if solution:
                logger.info(f"[ZEFOY_OCR] Tesseract (high contrast) solved: {solution}")
                return solution

        # Strategy 4: EasyOCR fallback
        if self._easyocr_available:
            solution = self._try_easyocr(image_bytes)
            if solution:
                logger.info(f"[ZEFOY_OCR] EasyOCR solved: {solution}")
                return solution

        # Strategy 5: LLM Vision fallback (Claude/OpenAI)
        solution = self._try_llm_vision(image_bytes)
        if solution:
            logger.info(f"[ZEFOY_OCR] LLM Vision solved: {solution}")
            return solution

        logger.warning("[ZEFOY_OCR] All OCR methods failed")
        return None

    async def solve_async(self, image_bytes: bytes) -> str | None:
        """Async version of solve."""
        try:
            loop = asyncio.get_event_loop()
            solution = await loop.run_in_executor(None, self.solve, image_bytes)
            return solution
        except Exception as e:
            logger.error("[ZEFOY_OCR] Async OCR failed", error=str(e))
            return None

    def _try_tesseract(self, image_bytes: bytes, preprocess: str = "default") -> str | None:
        """Try Tesseract with specific preprocessing."""
        try:
            from PIL import Image
            import pytesseract

            img = Image.open(io.BytesIO(image_bytes))

            if preprocess == "default":
                img = self._preprocess_image(img)
            elif preprocess == "inverted":
                img = self._preprocess_inverted(img)
            elif preprocess == "high_contrast":
                img = self._preprocess_high_contrast(img)

            # Try multiple Tesseract configs
            configs = [
                r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                r'--oem 3 --psm 6',
            ]

            for config in configs:
                text = pytesseract.image_to_string(img, config=config)
                solution = self._clean_solution(text)
                if solution:
                    logger.debug(f"[ZEFOY_OCR] Tesseract result: raw='{text.strip()}' clean='{solution}'")
                    return solution

        except Exception as e:
            logger.debug(f"[ZEFOY_OCR] Tesseract error: {e}")

        return None

    def _try_easyocr(self, image_bytes: bytes) -> str | None:
        """Try EasyOCR as fallback."""
        try:
            import easyocr
            from PIL import Image
            import numpy as np

            # Initialize reader (cached)
            if self._easyocr_reader is None:
                logger.info("[ZEFOY_OCR] Initializing EasyOCR (first time, may take a moment)...")
                self._easyocr_reader = easyocr.Reader(['en'], gpu=False)

            # Convert to numpy array
            img = Image.open(io.BytesIO(image_bytes))
            img_array = np.array(img)

            # Run OCR
            results = self._easyocr_reader.readtext(img_array)

            # Extract text
            texts = [r[1] for r in results]
            combined = ''.join(texts)
            solution = self._clean_solution(combined)

            if solution:
                logger.debug(f"[ZEFOY_OCR] EasyOCR result: raw='{combined}' clean='{solution}'")
                return solution

        except Exception as e:
            logger.debug(f"[ZEFOY_OCR] EasyOCR error: {e}")

        return None

    def _try_llm_vision(self, image_bytes: bytes) -> str | None:
        """Try LLM vision (Claude or OpenAI) as fallback."""
        import base64
        import os

        # Encode image to base64
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        # Try Anthropic Claude first
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=anthropic_key)
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=50,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_b64,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Read the captcha text in this image. Reply with ONLY the text/letters/numbers you see, nothing else. No explanation.",
                                },
                            ],
                        }
                    ],
                )
                raw_text = message.content[0].text.strip()
                solution = self._clean_solution(raw_text)
                if solution:
                    logger.debug(f"[ZEFOY_OCR] Claude result: raw='{raw_text}' clean='{solution}'")
                    return solution
            except Exception as e:
                logger.debug(f"[ZEFOY_OCR] Claude error: {e}")

        # Try OpenAI as fallback
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                import openai

                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=50,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Read the captcha text in this image. Reply with ONLY the text/letters/numbers you see, nothing else.",
                                },
                            ],
                        }
                    ],
                )
                raw_text = response.choices[0].message.content.strip()
                solution = self._clean_solution(raw_text)
                if solution:
                    logger.debug(f"[ZEFOY_OCR] OpenAI result: raw='{raw_text}' clean='{solution}'")
                    return solution
            except Exception as e:
                logger.debug(f"[ZEFOY_OCR] OpenAI error: {e}")

        return None

    def _preprocess_image(self, img: Any) -> Any:
        """Preprocess image for better OCR accuracy."""
        from PIL import ImageEnhance, ImageFilter, ImageOps

        # Convert to grayscale
        img = img.convert("L")

        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Binarize
        threshold = 128
        img = img.point(lambda p: 255 if p > threshold else 0)

        # Remove noise
        img = img.filter(ImageFilter.MedianFilter(size=3))

        # Invert if mostly dark
        pixels = list(img.getdata())
        avg_brightness = sum(pixels) / len(pixels)
        if avg_brightness < 128:
            img = ImageOps.invert(img)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        return img

    def _preprocess_inverted(self, img: Any) -> Any:
        """Preprocess with forced inversion."""
        from PIL import ImageEnhance, ImageFilter, ImageOps

        img = img.convert("L")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.5)
        threshold = 100
        img = img.point(lambda p: 255 if p > threshold else 0)
        img = ImageOps.invert(img)  # Force invert
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = img.filter(ImageFilter.SHARPEN)
        return img

    def _preprocess_high_contrast(self, img: Any) -> Any:
        """Preprocess with very high contrast."""
        from PIL import ImageEnhance, ImageFilter, ImageOps

        img = img.convert("L")
        # Very high contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(4.0)
        # Aggressive binarization
        threshold = 150
        img = img.point(lambda p: 255 if p > threshold else 0)
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.SHARPEN)  # Double sharpen
        return img

    def _clean_solution(self, text: str) -> str | None:
        """Clean up OCR result."""
        text = text.strip()
        text = re.sub(r'\s+', '', text)
        text = re.sub(r'[^a-zA-Z0-9]', '', text)

        # Zefoy captchas are typically 4-6 characters
        if text and 4 <= len(text) <= 8:
            return text

        return text if text else None
