"""Configuration models using Pydantic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConfig(BaseModel):
    """Browser engine configuration."""

    default: str = "patchright"
    fallback_chain: list[str] = ["patchright", "camoufox", "playwright"]
    headless: bool = True
    stealth_level: Literal["low", "medium", "high", "paranoid"] = "high"
    slow_mo: float = 0
    timeout: float = 30000
    args: list[str] = []


class ConcurrencyConfig(BaseModel):
    """Concurrency configuration."""

    max_workers: int = Field(default=10, ge=1, le=10000)  # Support up to 10K workers
    max_contexts_per_browser: int = Field(default=5, ge=1, le=100)  # More contexts per browser
    max_browsers: int = Field(default=1, ge=1, le=100)  # Multiple browser instances
    task_timeout: float = Field(default=120, ge=10)
    queue_size: int = Field(default=10000, ge=100)  # Larger queue
    context_recycle_after: int = Field(default=50, ge=1)  # Recycle context after N tasks
    worker_recycle_after: int = Field(default=100, ge=1)  # Recycle worker after N tasks
    memory_limit_mb: int = Field(default=0, ge=0)  # 0 = no limit

    class RetryConfig(BaseModel):
        """Retry configuration."""

        max_attempts: int = Field(default=3, ge=1, le=10)
        backoff_base: float = Field(default=2.0, ge=1.0)
        backoff_max: float = Field(default=60.0, ge=1.0)

    retry: RetryConfig = Field(default_factory=RetryConfig)


class FingerprintConfig(BaseModel):
    """Fingerprint configuration."""

    provider: str = "browserforge"
    device_profiles_path: Path | None = None
    randomize_per_session: bool = True
    consistency: Literal["strict", "loose"] = "strict"

    class ConstraintsConfig(BaseModel):
        """Fingerprint generation constraints."""

        browsers: list[str] = ["chrome", "firefox", "edge"]
        os_list: list[str] = ["windows", "macos", "linux"]
        min_version: int = 100

    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)


class ProxyProviderConfig(BaseModel):
    """Single proxy provider configuration."""

    type: str  # file, rotating, brightdata, oxylabs
    path: str | None = None
    format: str = "ip:port:user:pass"
    username: str | None = None
    password: str | None = None
    zone: str | None = None
    country: str | None = None
    api_key: str | None = None


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    rotation_strategy: Literal[
        "random", "round_robin", "weighted", "least_used", "fastest", "sticky"
    ] = "weighted"
    health_check_interval: int = Field(default=300, ge=60)
    max_consecutive_failures: int = Field(default=3, ge=1)
    providers: list[ProxyProviderConfig] = []


class EvasionConfig(BaseModel):
    """Anti-detection evasion configuration."""

    enabled: bool = True
    modules: list[str] = [
        "canvas_defense",
        "webgl_spoof",
        "battery_fake",
        "rtc_block",
        "font_mask",
        "timezone_geo",
    ]
    stealth_js_path: Path | None = None


class BehaviorConfig(BaseModel):
    """Human behavior simulation configuration."""

    human_simulation: bool = True
    mouse: Literal["bezier", "linear", "direct"] = "bezier"
    typing_wpm: tuple[int, int] = (40, 80)
    scroll: Literal["natural", "smooth", "instant"] = "natural"
    click_delay_ms: tuple[int, int] = (50, 200)
    dwell_time_s: tuple[float, float] = (5.0, 30.0)
    mistakes_enabled: bool = True
    mistake_rate: float = Field(default=0.02, ge=0, le=0.1)


class NetworkConfig(BaseModel):
    """Network configuration."""

    analytics_blocking: bool = True
    referrer_spoofing: bool = True
    request_interception: bool = False
    throttle: bool = False
    throttle_profile: Literal["3g", "4g", "wifi", "cable"] = "wifi"
    timeout: float = 30000


class CaptchaConfig(BaseModel):
    """CAPTCHA solver configuration."""

    enabled: bool = False
    solver: str = "2captcha"
    api_key: str | None = None
    timeout: float = 120
    retry_count: int = 2


class OutputConfig(BaseModel):
    """Output configuration."""

    class ScreenshotConfig(BaseModel):
        """Screenshot output configuration."""

        enabled: bool = True
        format: Literal["png", "jpeg", "webp"] = "png"
        quality: int = Field(default=80, ge=1, le=100)
        full_page: bool = False
        on_error: bool = True
        directory: Path = Path("./output/screenshots")

    class DataConfig(BaseModel):
        """Data output configuration."""

        format: Literal["json", "csv", "sqlite"] = "json"
        directory: Path = Path("./output/data")
        batch_size: int = Field(default=100, ge=1)

    class LogConfig(BaseModel):
        """Logging configuration."""

        level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
        structured: bool = True
        file: Path | None = None
        max_size_mb: int = Field(default=100, ge=1)
        backup_count: int = Field(default=5, ge=1)

    screenshots: ScreenshotConfig = Field(default_factory=ScreenshotConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    logs: LogConfig = Field(default_factory=LogConfig)


class PluginConfig(BaseModel):
    """Plugin configuration."""

    enabled: bool = True
    directory: Path = Path("./plugins")
    autoload: bool = True
    disabled: list[str] = []


class WatchdogSystemConfig(BaseModel):
    """Watchdog system configuration."""

    enabled: bool = True
    health_check_interval: float = Field(default=30.0, ge=1.0)
    auto_recovery: bool = True
    max_recovery_attempts: int = Field(default=3, ge=1)
    recovery_cooldown: float = Field(default=5.0, ge=1.0)
    alert_threshold: int = Field(default=3, ge=1)
    browser_timeout: float = Field(default=60.0, ge=10.0)
    page_timeout: float = Field(default=30.0, ge=5.0)
    network_timeout: float = Field(default=15.0, ge=5.0)


class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    api_key: str = ""
    model: str = ""
    base_url: str | None = None


class VisionSettingsConfig(BaseModel):
    """Vision/screenshot analysis configuration."""

    mode: Literal["off", "auto", "always"] = "auto"  # off=DOM only, auto=fallback, always=screenshot
    detail_level: Literal["low", "high", "auto"] = "auto"
    max_width: int = Field(default=1280, ge=640, le=3840)
    max_height: int = Field(default=800, ge=480, le=2160)
    fallback_threshold: float = Field(default=0.6, ge=0, le=1)  # Use vision if DOM confidence below this


class LLMConfig(BaseModel):
    """LLM integration configuration."""

    enabled: bool = False
    default_provider: Literal["openai", "anthropic", "ollama"] = "openai"

    # Provider configs
    openai: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(model="gpt-4o"))
    anthropic: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(model="claude-sonnet-4-20250514"))
    ollama: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        model="llama3",
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    ))

    # Shared settings
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int | None = None
    timeout: float = Field(default=60.0, ge=10.0)
    max_retries: int = Field(default=3, ge=1)

    # Controller settings
    controller_mode: Literal["assist", "autonomous"] = "assist"
    max_steps: int = Field(default=20, ge=1, le=100)
    min_confidence: float = Field(default=0.5, ge=0, le=1)

    # Vision settings (hybrid DOM+Vision mode like browser-use)
    vision: VisionSettingsConfig = Field(default_factory=VisionSettingsConfig)


class DOMConfig(BaseModel):
    """DOM intelligence configuration."""

    enabled: bool = False
    extract_on_load: bool = False  # Auto-extract after page load
    include_hidden: bool = False
    max_depth: int = Field(default=10, ge=1, le=50)
    include_styles: bool = True
    include_attributes: bool = True


class Config(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PHANTOM_SURGE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Core settings
    engine: EngineConfig = Field(default_factory=EngineConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    fingerprint: FingerprintConfig = Field(default_factory=FingerprintConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    evasion: EvasionConfig = Field(default_factory=EvasionConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    captcha: CaptchaConfig = Field(default_factory=CaptchaConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    watchdog: WatchdogSystemConfig = Field(default_factory=WatchdogSystemConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    dom: DOMConfig = Field(default_factory=DOMConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> Config:
        """Load configuration from YAML file."""
        import yaml

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open() as f:
            data = yaml.safe_load(f)

        return cls(**data) if data else cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create configuration from dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    def to_yaml(self, path: Path | str) -> None:
        """Save configuration to YAML file."""
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    def merge(self, other: Config) -> Config:
        """Merge with another config, other takes precedence."""
        self_dict = self.model_dump()
        other_dict = other.model_dump()

        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        merged = deep_merge(self_dict, other_dict)
        return Config(**merged)
