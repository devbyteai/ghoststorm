"""CAPTCHA solving plugins using local AI models.

Provides CAPTCHA solving without paid services using:
- YOLO vision models for image CAPTCHAs
- Local LLMs (Ollama) for complex CAPTCHAs
- Whisper for audio CAPTCHA transcription
"""

from ghoststorm.plugins.captcha.solver import (
    CaptchaResult,
    CaptchaSolver,
    CaptchaSolverConfig,
    CaptchaType,
    SolverProvider,
)

__all__ = [
    "CaptchaResult",
    "CaptchaSolver",
    "CaptchaSolverConfig",
    "CaptchaType",
    "SolverProvider",
]
