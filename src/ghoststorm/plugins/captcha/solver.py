"""CAPTCHA solver framework using local AI models.

Enterprise-grade CAPTCHA solving without paid services:
- YOLO vision models for image selection CAPTCHAs
- Local LLMs (Ollama/llama.cpp) for complex reasoning
- Whisper for audio CAPTCHA transcription
- CNN-BiLSTM for distorted text CAPTCHAs

Supports:
- reCAPTCHA v2 (image and audio)
- hCaptcha (image selection)
- Custom image CAPTCHAs
- Text-based CAPTCHAs
- Cloudflare Turnstile (partial)

Research References:
- YOLO CAPTCHA benchmark (arXiv:2502.13740)
- i-am-a-bot multi-modal LLM agent
- Buster audio CAPTCHA solver
"""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CaptchaType(str, Enum):
    """Types of CAPTCHAs supported."""

    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    IMAGE_SELECTION = "image_selection"
    TEXT_DISTORTED = "text_distorted"
    MATH_EQUATION = "math_equation"
    AUDIO = "audio"
    CUSTOM = "custom"


class SolverProvider(str, Enum):
    """CAPTCHA solver providers."""

    YOLO = "yolo"  # YOLO vision model
    LLM = "llm"  # Local LLM (Ollama)
    WHISPER = "whisper"  # Audio transcription
    CNN = "cnn"  # CNN for text
    AUTO = "auto"  # Auto-select best


@dataclass
class CaptchaResult:
    """Result from CAPTCHA solving attempt."""

    success: bool
    solution: str | list[int] | None = None  # Text or selected indices
    confidence: float = 0.0
    solver_used: SolverProvider | None = None
    time_taken: float = 0.0  # seconds
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaptchaChallenge:
    """CAPTCHA challenge to solve."""

    captcha_type: CaptchaType
    image_data: bytes | None = None  # Image bytes
    image_url: str | None = None  # Image URL
    audio_data: bytes | None = None  # Audio bytes
    audio_url: str | None = None  # Audio URL
    prompt: str | None = None  # Challenge prompt (e.g., "Select all traffic lights")
    grid_size: tuple[int, int] = (3, 3)  # For image selection
    site_key: str | None = None  # reCAPTCHA/hCaptcha site key
    page_url: str | None = None  # Page URL for context
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaptchaSolverConfig:
    """Configuration for CAPTCHA solver."""

    # Model paths
    yolo_model_path: Path | None = None
    whisper_model: str = "base"  # tiny, base, small, medium, large

    # LLM settings
    ollama_model: str = "llava:7b"  # Vision-capable LLM
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )

    # Provider preferences
    preferred_provider: SolverProvider = SolverProvider.AUTO

    # Timeout settings
    solve_timeout: float = 30.0  # seconds

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    # GPU acceleration
    use_gpu: bool = True


class SolverBackend(ABC):
    """Abstract base for solver backends."""

    @abstractmethod
    async def solve(self, challenge: CaptchaChallenge) -> CaptchaResult:
        """Solve a CAPTCHA challenge."""
        pass

    @abstractmethod
    def supports(self, captcha_type: CaptchaType) -> bool:
        """Check if backend supports this CAPTCHA type."""
        pass


class YOLOSolver(SolverBackend):
    """YOLO-based image CAPTCHA solver.

    Uses YOLO object detection to identify and select
    correct images in selection-based CAPTCHAs.
    """

    def __init__(self, model_path: Path | None = None, use_gpu: bool = True) -> None:
        self.model_path = model_path
        self.use_gpu = use_gpu
        self._model: Any = None
        self._loaded = False

    async def _load_model(self) -> None:
        """Load YOLO model."""
        if self._loaded:
            return

        try:
            from ultralytics import YOLO

            if self.model_path and self.model_path.exists():
                self._model = YOLO(str(self.model_path))
            else:
                # Use pretrained YOLOv8
                self._model = YOLO("yolov8n.pt")

            self._loaded = True
            logger.info("YOLO model loaded", model=str(self.model_path))
        except ImportError:
            logger.error("ultralytics not installed. Install with: pip install ultralytics")
            raise
        except Exception as e:
            logger.error("Failed to load YOLO model", error=str(e))
            raise

    def supports(self, captcha_type: CaptchaType) -> bool:
        """Check supported types."""
        return captcha_type in [
            CaptchaType.IMAGE_SELECTION,
            CaptchaType.HCAPTCHA,
            CaptchaType.RECAPTCHA_V2,
        ]

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaResult:
        """Solve image selection CAPTCHA using YOLO."""
        import time

        start_time = time.time()

        try:
            await self._load_model()

            # Get image data
            if challenge.image_data:
                image_bytes = challenge.image_data
            elif challenge.image_url:
                # Fetch image
                image_bytes = await self._fetch_image(challenge.image_url)
            else:
                return CaptchaResult(
                    success=False,
                    error="No image provided",
                    solver_used=SolverProvider.YOLO,
                )

            # Parse prompt to determine target class
            target_classes = self._parse_prompt(challenge.prompt or "")

            # Run detection
            results = self._model(image_bytes)

            # Find matching cells
            selected_indices = self._find_matching_cells(
                results,
                target_classes,
                challenge.grid_size,
            )

            return CaptchaResult(
                success=len(selected_indices) > 0,
                solution=selected_indices,
                confidence=0.8 if selected_indices else 0.0,
                solver_used=SolverProvider.YOLO,
                time_taken=time.time() - start_time,
                metadata={"target_classes": target_classes},
            )

        except Exception as e:
            logger.error("YOLO solver failed", error=str(e))
            return CaptchaResult(
                success=False,
                error=str(e),
                solver_used=SolverProvider.YOLO,
                time_taken=time.time() - start_time,
            )

    async def _fetch_image(self, url: str) -> bytes:
        """Fetch image from URL."""
        import aiohttp

        async with aiohttp.ClientSession() as session, session.get(url) as response:
            return await response.read()

    def _parse_prompt(self, prompt: str) -> list[str]:
        """Parse CAPTCHA prompt to get target object classes."""
        prompt_lower = prompt.lower()

        # Common CAPTCHA target mappings
        target_map = {
            "traffic light": ["traffic light"],
            "crosswalk": ["person", "pedestrian"],
            "bus": ["bus"],
            "bicycle": ["bicycle"],
            "motorcycle": ["motorcycle"],
            "car": ["car", "truck"],
            "fire hydrant": ["fire hydrant"],
            "parking meter": ["parking meter"],
            "boat": ["boat"],
            "plane": ["airplane"],
            "bridge": ["bridge"],
            "stairs": ["stairs"],
            "mountain": ["mountain"],
            "palm tree": ["tree"],
            "chimney": ["chimney"],
            "tractor": ["tractor"],
        }

        for key, classes in target_map.items():
            if key in prompt_lower:
                return classes

        # Default to prompt words as classes
        return prompt_lower.split()

    def _find_matching_cells(
        self,
        results: Any,
        target_classes: list[str],
        grid_size: tuple[int, int],
    ) -> list[int]:
        """Find grid cells containing target objects."""
        if not results or len(results) == 0:
            return []

        result = results[0]
        if not hasattr(result, "boxes") or len(result.boxes) == 0:
            return []

        # Get image dimensions
        img_width = result.orig_shape[1]
        img_height = result.orig_shape[0]

        # Calculate cell dimensions
        cell_width = img_width / grid_size[0]
        cell_height = img_height / grid_size[1]

        # Track which cells have matches
        selected_cells = set()

        # Check each detection
        for _i, box in enumerate(result.boxes):
            class_id = int(box.cls[0])
            class_name = result.names[class_id].lower()
            confidence = float(box.conf[0])

            # Check if class matches targets
            if any(target in class_name for target in target_classes):
                if confidence > 0.3:  # Confidence threshold
                    # Get box center
                    x1, y1, x2, y2 = box.xyxy[0]
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2

                    # Calculate cell index
                    col = int(center_x / cell_width)
                    row = int(center_y / cell_height)
                    cell_index = row * grid_size[0] + col

                    if 0 <= cell_index < grid_size[0] * grid_size[1]:
                        selected_cells.add(cell_index)

        return sorted(selected_cells)


class LLMSolver(SolverBackend):
    """LLM-based CAPTCHA solver using Ollama.

    Uses vision-capable LLMs (like LLaVA) for complex
    reasoning about CAPTCHA challenges.
    """

    def __init__(
        self,
        model: str = "llava:7b",
        host: str | None = None,
    ) -> None:
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def supports(self, captcha_type: CaptchaType) -> bool:
        """Check supported types."""
        return captcha_type in [
            CaptchaType.IMAGE_SELECTION,
            CaptchaType.TEXT_DISTORTED,
            CaptchaType.MATH_EQUATION,
            CaptchaType.CUSTOM,
        ]

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaResult:
        """Solve CAPTCHA using LLM."""
        import time

        start_time = time.time()

        try:
            import aiohttp

            # Prepare prompt based on challenge type
            if challenge.captcha_type == CaptchaType.IMAGE_SELECTION:
                prompt = self._build_image_selection_prompt(challenge)
            elif challenge.captcha_type == CaptchaType.TEXT_DISTORTED:
                prompt = "Read and transcribe the text shown in this image exactly as it appears."
            elif challenge.captcha_type == CaptchaType.MATH_EQUATION:
                prompt = "Solve the math equation shown in this image and return only the numeric answer."
            else:
                prompt = challenge.prompt or "Describe what you see in this image."

            # Prepare image
            if challenge.image_data:
                image_b64 = base64.b64encode(challenge.image_data).decode()
            else:
                return CaptchaResult(
                    success=False,
                    error="No image provided",
                    solver_used=SolverProvider.LLM,
                )

            # Call Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
            }

            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self.host}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response,
            ):
                if response.status != 200:
                    error_text = await response.text()
                    return CaptchaResult(
                        success=False,
                        error=f"Ollama API error: {error_text}",
                        solver_used=SolverProvider.LLM,
                    )

                result = await response.json()
                answer = result.get("response", "").strip()

            # Parse answer based on challenge type
            solution = self._parse_answer(answer, challenge)

            return CaptchaResult(
                success=solution is not None,
                solution=solution,
                confidence=0.7,
                solver_used=SolverProvider.LLM,
                time_taken=time.time() - start_time,
                metadata={"raw_answer": answer},
            )

        except Exception as e:
            logger.error("LLM solver failed", error=str(e))
            return CaptchaResult(
                success=False,
                error=str(e),
                solver_used=SolverProvider.LLM,
                time_taken=time.time() - start_time,
            )

    def _build_image_selection_prompt(self, challenge: CaptchaChallenge) -> str:
        """Build prompt for image selection CAPTCHA."""
        grid_w, grid_h = challenge.grid_size
        prompt = f"""This is a {grid_w}x{grid_h} grid CAPTCHA image.
The challenge asks: "{challenge.prompt}"

Please identify which cells (numbered 0-{grid_w * grid_h - 1}, left to right, top to bottom)
contain the requested objects.

Return ONLY the cell numbers separated by commas.
Example: 0,3,6"""
        return prompt

    def _parse_answer(
        self,
        answer: str,
        challenge: CaptchaChallenge,
    ) -> str | list[int] | None:
        """Parse LLM answer to solution format."""
        if challenge.captcha_type == CaptchaType.IMAGE_SELECTION:
            # Extract numbers from answer
            import re

            numbers = re.findall(r"\d+", answer)
            if numbers:
                max_cell = challenge.grid_size[0] * challenge.grid_size[1]
                return [int(n) for n in numbers if int(n) < max_cell]
            return None

        # For text/math, return cleaned answer
        return answer.strip()


class WhisperSolver(SolverBackend):
    """Audio CAPTCHA solver using Whisper.

    Transcribes audio CAPTCHAs using OpenAI's Whisper model.
    """

    def __init__(self, model: str = "base") -> None:
        self.model_name = model
        self._model: Any = None
        self._loaded = False

    async def _load_model(self) -> None:
        """Load Whisper model."""
        if self._loaded:
            return

        try:
            import whisper

            self._model = whisper.load_model(self.model_name)
            self._loaded = True
            logger.info("Whisper model loaded", model=self.model_name)
        except ImportError:
            logger.error("openai-whisper not installed. Install with: pip install openai-whisper")
            raise
        except Exception as e:
            logger.error("Failed to load Whisper model", error=str(e))
            raise

    def supports(self, captcha_type: CaptchaType) -> bool:
        """Check supported types."""
        return captcha_type in [CaptchaType.AUDIO, CaptchaType.RECAPTCHA_V2]

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaResult:
        """Solve audio CAPTCHA using Whisper."""
        import time

        start_time = time.time()

        try:
            await self._load_model()

            # Get audio data
            if challenge.audio_data:
                audio_bytes = challenge.audio_data
            elif challenge.audio_url:
                audio_bytes = await self._fetch_audio(challenge.audio_url)
            else:
                return CaptchaResult(
                    success=False,
                    error="No audio provided",
                    solver_used=SolverProvider.WHISPER,
                )

            # Save to temp file for Whisper
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                # Transcribe
                result = self._model.transcribe(
                    temp_path,
                    language="en",
                    task="transcribe",
                )
                text = result.get("text", "").strip()

                # Clean up transcription for CAPTCHA
                # Remove punctuation, lowercase, extract alphanumeric
                import re

                cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", text).lower()
                # Remove common filler words
                cleaned = re.sub(
                    r"\b(the|a|an|is|are|to|of)\b",
                    "",
                    cleaned,
                    flags=re.IGNORECASE,
                )
                cleaned = " ".join(cleaned.split())

                return CaptchaResult(
                    success=bool(cleaned),
                    solution=cleaned,
                    confidence=0.75,
                    solver_used=SolverProvider.WHISPER,
                    time_taken=time.time() - start_time,
                    metadata={"raw_text": text},
                )

            finally:
                # Cleanup temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error("Whisper solver failed", error=str(e))
            return CaptchaResult(
                success=False,
                error=str(e),
                solver_used=SolverProvider.WHISPER,
                time_taken=time.time() - start_time,
            )

    async def _fetch_audio(self, url: str) -> bytes:
        """Fetch audio from URL."""
        import aiohttp

        async with aiohttp.ClientSession() as session, session.get(url) as response:
            return await response.read()


class CaptchaSolver:
    """Main CAPTCHA solver orchestrator.

    Automatically selects the best solver backend based on
    challenge type and available models.

    Usage:
        solver = CaptchaSolver()

        # For image selection CAPTCHA
        challenge = CaptchaChallenge(
            captcha_type=CaptchaType.IMAGE_SELECTION,
            image_data=image_bytes,
            prompt="Select all traffic lights",
            grid_size=(3, 3),
        )
        result = await solver.solve(challenge)

        if result.success:
            # Click cells at result.solution indices
            pass
    """

    def __init__(self, config: CaptchaSolverConfig | None = None) -> None:
        """Initialize CAPTCHA solver.

        Args:
            config: Solver configuration
        """
        self.config = config or CaptchaSolverConfig()
        self._backends: dict[SolverProvider, SolverBackend] = {}
        self._initialized = False

    def _init_backends(self) -> None:
        """Initialize solver backends."""
        if self._initialized:
            return

        # Initialize YOLO solver
        try:
            self._backends[SolverProvider.YOLO] = YOLOSolver(
                model_path=self.config.yolo_model_path,
                use_gpu=self.config.use_gpu,
            )
        except Exception as e:
            logger.warning("YOLO solver not available", error=str(e))

        # Initialize LLM solver
        try:
            self._backends[SolverProvider.LLM] = LLMSolver(
                model=self.config.ollama_model,
                host=self.config.ollama_host,
            )
        except Exception as e:
            logger.warning("LLM solver not available", error=str(e))

        # Initialize Whisper solver
        try:
            self._backends[SolverProvider.WHISPER] = WhisperSolver(
                model=self.config.whisper_model,
            )
        except Exception as e:
            logger.warning("Whisper solver not available", error=str(e))

        self._initialized = True

    async def solve(
        self,
        challenge: CaptchaChallenge,
        provider: SolverProvider | None = None,
    ) -> CaptchaResult:
        """Solve a CAPTCHA challenge.

        Args:
            challenge: CAPTCHA challenge to solve
            provider: Specific provider to use (auto-select if None)

        Returns:
            CaptchaResult with solution or error
        """
        self._init_backends()

        # Select provider
        if provider is None or provider == SolverProvider.AUTO:
            provider = self._select_provider(challenge)

        if provider not in self._backends:
            return CaptchaResult(
                success=False,
                error=f"Provider {provider} not available",
            )

        backend = self._backends[provider]

        # Try with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                result = await asyncio.wait_for(
                    backend.solve(challenge),
                    timeout=self.config.solve_timeout,
                )

                if result.success:
                    return result

                last_error = result.error

            except TimeoutError:
                last_error = "Solver timeout"

            except Exception as e:
                last_error = str(e)

            # Delay before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay)

        return CaptchaResult(
            success=False,
            error=last_error or "All attempts failed",
            solver_used=provider,
        )

    def _select_provider(self, challenge: CaptchaChallenge) -> SolverProvider:
        """Select best provider for challenge type."""
        # Priority order based on challenge type
        if challenge.captcha_type == CaptchaType.AUDIO:
            return SolverProvider.WHISPER

        if challenge.captcha_type in [
            CaptchaType.IMAGE_SELECTION,
            CaptchaType.HCAPTCHA,
        ]:
            # Prefer YOLO for image selection
            if SolverProvider.YOLO in self._backends:
                return SolverProvider.YOLO
            return SolverProvider.LLM

        if challenge.captcha_type in [
            CaptchaType.TEXT_DISTORTED,
            CaptchaType.MATH_EQUATION,
        ]:
            return SolverProvider.LLM

        # Default to config preference
        if self.config.preferred_provider in self._backends:
            return self.config.preferred_provider

        # Return first available
        if self._backends:
            return next(iter(self._backends.keys()))

        return SolverProvider.LLM
