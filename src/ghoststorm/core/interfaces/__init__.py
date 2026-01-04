"""Core interfaces (protocols) for plugin system."""

from ghoststorm.core.interfaces.behavior import IBehaviorSimulator
from ghoststorm.core.interfaces.browser import IBrowserContext, IBrowserEngine, IPage
from ghoststorm.core.interfaces.captcha import ICaptchaSolver
from ghoststorm.core.interfaces.extractor import IDataExtractor
from ghoststorm.core.interfaces.fingerprint import IFingerprintGenerator
from ghoststorm.core.interfaces.output import IOutputWriter
from ghoststorm.core.interfaces.proxy import IProxyProvider

__all__ = [
    "IBehaviorSimulator",
    "IBrowserContext",
    "IBrowserEngine",
    "ICaptchaSolver",
    "IDataExtractor",
    "IFingerprintGenerator",
    "IOutputWriter",
    "IPage",
    "IProxyProvider",
]
