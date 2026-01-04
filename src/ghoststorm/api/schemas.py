"""Pydantic schemas for API request/response models."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Platform types
PlatformType = Literal["tiktok", "instagram", "youtube", "dextools", "generic"]
TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
ExecutionMode = Literal["batch", "debug"]

# LLM/AI types
LLMMode = Literal["off", "assist", "autonomous"]
VisionMode = Literal["off", "auto", "always"]


# URL Detection patterns
PLATFORM_PATTERNS: dict[str, list[str]] = {
    "tiktok": [
        r"tiktok\.com/@[\w.]+/video/(\d+)",
        r"tiktok\.com/@([\w.]+)$",
        r"vm\.tiktok\.com/(\w+)",
        r"tiktok\.com/t/(\w+)",
    ],
    "instagram": [
        r"instagram\.com/reel/([\w-]+)",
        r"instagram\.com/p/([\w-]+)",
        r"instagram\.com/stories/([\w.]+)/(\d+)",
        r"instagram\.com/([\w.]+)/?$",
    ],
    "youtube": [
        r"youtube\.com/watch\?v=([\w-]+)",
        r"youtube\.com/shorts/([\w-]+)",
        r"youtu\.be/([\w-]+)",
        r"youtube\.com/@([\w]+)",
        r"youtube\.com/channel/([\w-]+)",
    ],
    "dextools": [
        r"dextools\.io/app/[\w-]+/pair-explorer/(0x[\w]+)",
    ],
}


def detect_platform(url: str) -> tuple[PlatformType, dict[str, str]]:
    """Auto-detect platform from URL and extract metadata.

    Returns:
        Tuple of (platform_type, metadata_dict)
    """
    url = url.strip()

    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                metadata: dict[str, str] = {"url": url}

                # Extract ID/username based on platform
                if platform == "tiktok":
                    groups = match.groups()
                    if "video" in url.lower():
                        metadata["video_id"] = groups[0]
                    else:
                        metadata["username"] = groups[0]
                elif platform == "instagram":
                    groups = match.groups()
                    if "reel" in url.lower() or "/p/" in url.lower():
                        metadata["post_id"] = groups[0]
                    elif "stories" in url.lower():
                        metadata["username"] = groups[0]
                        metadata["story_id"] = groups[1]
                    else:
                        metadata["username"] = groups[0]
                elif platform == "youtube":
                    groups = match.groups()
                    if "watch" in url.lower() or "youtu.be" in url.lower():
                        metadata["video_id"] = groups[0]
                    elif "shorts" in url.lower():
                        metadata["short_id"] = groups[0]
                    else:
                        metadata["channel"] = groups[0]
                elif platform == "dextools":
                    metadata["pair_address"] = match.groups()[0]

                return platform, metadata  # type: ignore

    return "generic", {"url": url}


# --- Task Schemas ---


class TaskCreate(BaseModel):
    """Request schema for creating a new task."""

    url: str = Field(..., description="Target URL to process")
    platform: PlatformType | None = Field(
        None, description="Platform type (auto-detected if not provided)"
    )
    mode: ExecutionMode = Field(
        "batch", description="Execution mode: batch (multi-worker) or debug (single)"
    )
    workers: int = Field(1, ge=1, le=50, description="Number of concurrent workers")
    repeat: int = Field(1, ge=1, le=1000, description="Number of times to repeat task")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific configuration overrides"
    )

    # LLM/AI control
    llm_mode: LLMMode = Field(
        "off",
        description="LLM control mode: off (manual), assist (AI suggests), autonomous (AI executes)",
    )
    llm_task: str | None = Field(
        None, description="Natural language goal for LLM (e.g., 'Watch 5 videos and like each')"
    )
    vision_mode: VisionMode = Field(
        "auto", description="Vision mode: off (DOM only), auto (fallback), always (screenshot)"
    )

    # Enhanced behavior configuration (Step 5)
    behavior: dict[str, Any] | None = Field(
        None, description="Enhanced behavior configuration from Step 5 wizard"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class TaskResponse(BaseModel):
    """Response schema for task information."""

    task_id: str
    status: TaskStatus
    platform: PlatformType
    url: str
    mode: ExecutionMode
    workers: int
    progress: float = Field(ge=0, le=1)
    results: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # LLM/AI fields
    llm_mode: LLMMode = "off"
    llm_task: str | None = None
    vision_mode: VisionMode = "auto"
    llm_analysis: dict[str, Any] | None = None  # Latest LLM analysis/suggestions


class TaskListResponse(BaseModel):
    """Response schema for task list."""

    tasks: list[TaskResponse]
    total: int
    running: int
    completed: int
    failed: int


# --- Platform Config Schemas ---


class TikTokConfigSchema(BaseModel):
    """TikTok automation configuration."""

    target_video_urls: list[str] = Field(
        default_factory=list, description="Direct video URLs to watch"
    )
    min_watch_percent: float = Field(0.3, ge=0, le=1, description="Min watch %")
    max_watch_percent: float = Field(1.5, ge=0, le=3, description="Max watch %")
    skip_probability: float = Field(0.30, ge=0, le=1, description="Skip chance")
    bio_click_probability: float = Field(0.15, ge=0, le=1, description="Bio click chance")
    profile_visit_probability: float = Field(0.10, ge=0, le=1)
    videos_per_session_min: int = Field(10, ge=1)
    videos_per_session_max: int = Field(30, ge=1)
    swipe_speed_min: int = Field(300, ge=100, description="Swipe speed min (ms)")
    swipe_speed_max: int = Field(800, ge=100, description="Swipe speed max (ms)")
    inapp_dwell_time_min: float = Field(10.0, ge=1)
    inapp_dwell_time_max: float = Field(60.0, ge=1)


class InstagramConfigSchema(BaseModel):
    """Instagram automation configuration."""

    target_reel_urls: list[str] = Field(
        default_factory=list, description="Direct reel URLs to watch"
    )
    min_reel_watch_percent: float = Field(0.4, ge=0, le=1)
    max_reel_watch_percent: float = Field(1.2, ge=0, le=2)
    reel_skip_probability: float = Field(0.35, ge=0, le=1)
    story_skip_probability: float = Field(0.20, ge=0, le=1)
    story_link_click_probability: float = Field(0.25, ge=0, le=1)
    bio_link_click_probability: float = Field(0.20, ge=0, le=1)
    profile_visit_probability: float = Field(0.12, ge=0, le=1)
    reels_per_session_min: int = Field(5, ge=1)
    reels_per_session_max: int = Field(20, ge=1)
    simulate_inapp_browser: bool = Field(True, description="Simulate in-app browser")
    inapp_dwell_time_min: float = Field(10.0, ge=1)
    inapp_dwell_time_max: float = Field(60.0, ge=1)


class YouTubeConfigSchema(BaseModel):
    """YouTube automation configuration."""

    target_video_urls: list[str] = Field(
        default_factory=list, description="Direct video URLs to watch"
    )
    target_short_urls: list[str] = Field(
        default_factory=list, description="Direct short URLs to watch"
    )
    content_mode: Literal["videos", "shorts", "mixed"] = Field(
        "videos", description="Content type to watch"
    )
    min_watch_percent: float = Field(0.30, ge=0, le=1)
    max_watch_percent: float = Field(0.90, ge=0, le=1)
    min_watch_seconds: float = Field(30.0, ge=1, description="Min watch time (30s for view)")
    skip_probability: float = Field(0.20, ge=0, le=1)
    description_click_probability: float = Field(0.10, ge=0, le=1)
    channel_visit_probability: float = Field(0.08, ge=0, le=1)
    videos_per_session_min: int = Field(5, ge=1)
    videos_per_session_max: int = Field(15, ge=1)
    shorts_per_session_min: int = Field(10, ge=1)
    shorts_per_session_max: int = Field(30, ge=1)


class DEXToolsConfigSchema(BaseModel):
    """DEXTools automation configuration."""

    pair_url: str = Field("", description="DEXTools pair URL")

    # === Campaign Settings ===
    mode: Literal["single", "campaign"] = Field(
        "single", description="Visit mode: single visit or trending campaign"
    )
    num_visitors: int = Field(100, ge=1, le=10000, description="Visitors for campaign mode")
    duration_hours: float = Field(24.0, ge=0.5, le=168, description="Campaign duration (hours)")
    max_concurrent: int = Field(5, ge=1, le=50, description="Max concurrent visitors")
    distribution_mode: Literal["natural", "even", "burst"] = Field(
        "natural", description="How to distribute visits over time"
    )

    # === Behavior Settings ===
    behavior_mode: Literal["realistic", "passive", "light", "engaged", "custom"] = Field(
        "realistic",
        description="realistic (60% passive, 30% light, 10% engaged), or force specific behavior",
    )
    dwell_time_min: float = Field(30.0, ge=1, description="Min time on page (seconds)")
    dwell_time_max: float = Field(120.0, ge=1, description="Max time on page (seconds)")

    # === Action Settings ===
    enable_natural_scroll: bool = Field(True, description="Natural scroll behavior")
    enable_chart_hover: bool = Field(True, description="Hover over price chart")
    enable_mouse_movement: bool = Field(True, description="Bezier curve mouse movement")
    enable_social_clicks: bool = Field(True, description="Click social links (Twitter, Telegram)")
    enable_tab_clicks: bool = Field(False, description="Click chart tabs")
    enable_favorite: bool = Field(False, description="Click favorite/star button")

    # === Legacy Settings (backward compat) ===
    click_social_links: bool = Field(True, description="[Deprecated] Use enable_social_clicks")
    click_chart_tabs: bool = Field(False, description="[Deprecated] Use enable_tab_clicks")


class GenericConfigSchema(BaseModel):
    """Generic URL automation configuration."""

    dwell_time_min: float = Field(10.0, ge=1)
    dwell_time_max: float = Field(60.0, ge=1)
    click_links: bool = Field(False)
    scroll_page: bool = Field(True)


class EngineConfigSchema(BaseModel):
    """Core engine configuration."""

    workers: int = Field(5, ge=1, le=50, description="Concurrent workers")
    proxy_provider: Literal["none", "file", "rotating", "tor"] = Field("file")
    fingerprint_rotation: Literal["per_request", "per_session", "fixed"] = Field("per_session")
    browser_engine: Literal["patchright", "playwright", "camoufox"] = Field("patchright")
    headless: bool = Field(True, description="Run in headless mode")
    evasion_level: Literal["minimal", "standard", "maximum"] = Field("maximum")
    request_timeout: float = Field(30.0, ge=5)
    retry_attempts: int = Field(3, ge=0, le=10)


class BehaviorConfigSchema(BaseModel):
    """Behavior simulation configuration."""

    mouse_movement: Literal["bezier", "linear", "direct"] = Field("bezier")
    typing_speed_min: int = Field(40, ge=10, description="WPM min")
    typing_speed_max: int = Field(80, ge=10, description="WPM max")
    scroll_behavior: Literal["natural", "smooth", "instant"] = Field("natural")
    session_duration_min: float = Field(5.0, ge=1, description="Minutes")
    session_duration_max: float = Field(20.0, ge=1, description="Minutes")


# --- Enhanced Behavior Schemas (Step 5) ---

# Type definitions
BehaviorMode = Literal["preset", "llm", "hybrid"]
ReferrerMode = Literal["realistic", "custom", "none"]
MouseStyle = Literal["natural", "fast", "slow", "nervous", "confident", "random"]
ScrollBehavior = Literal["smooth", "reading", "jump", "minimal"]
EngagementLevel = Literal["passive", "active", "deep"]
LLMProvider = Literal["openai", "anthropic", "ollama"]
LLMPersonality = Literal["casual", "researcher", "shopper", "scanner", "custom"]
DecisionFrequency = Literal["every", "key", "fallback"]


class LLMBehaviorConfig(BaseModel):
    """LLM configuration for behavior decisions."""

    provider: LLMProvider = Field("openai", description="LLM provider")
    model: str = Field("gpt-4o", description="Model name")
    personality: LLMPersonality = Field("casual", description="Browsing personality")
    custom_prompt: str | None = Field(
        None, description="Custom behavior prompt when personality=custom"
    )
    decision_frequency: DecisionFrequency = Field(
        "key", description="How often LLM makes decisions"
    )
    vision_enabled: bool = Field(False, description="Enable screenshot analysis")
    temperature: float = Field(0.3, ge=0, le=1, description="LLM temperature")


class ReferrerConfigSchema(BaseModel):
    """Smart referrer distribution configuration."""

    mode: ReferrerMode = Field("realistic", description="Distribution mode")
    preset: str | None = Field(
        "realistic", description="Preset name: realistic, search_heavy, social_viral"
    )

    # Custom weights (when mode=custom)
    direct_weight: int = Field(45, ge=0, le=100, description="Direct traffic %")
    google_weight: int = Field(25, ge=0, le=100, description="Google search %")
    bing_weight: int = Field(5, ge=0, le=100, description="Bing search %")
    social_weight: int = Field(12, ge=0, le=100, description="Social media %")
    referral_weight: int = Field(8, ge=0, le=100, description="Other referrals %")
    email_weight: int = Field(3, ge=0, le=100, description="Email campaigns %")
    ai_search_weight: int = Field(2, ge=0, le=100, description="AI search (ChatGPT, Perplexity) %")

    # Variance to avoid detection patterns
    variance_percent: int = Field(10, ge=0, le=30, description="Randomization variance ±%")

    # Social platform selection
    social_platforms: list[str] = Field(
        default_factory=lambda: ["twitter", "reddit", "facebook", "linkedin"],
        description="Which social platforms to include",
    )


class InteractionConfigSchema(BaseModel):
    """Mouse, scroll, and interaction pattern configuration."""

    mouse_style: MouseStyle = Field("natural", description="Mouse movement style")
    scroll_behavior: ScrollBehavior = Field("smooth", description="Scroll behavior pattern")

    # Advanced mouse settings
    tremor_amplitude: float = Field(1.5, ge=0, le=5, description="Hand tremor simulation")
    overshoot_probability: float = Field(0.15, ge=0, le=0.5, description="Mouse overshoot chance")
    speed_multiplier: float = Field(1.0, ge=0.3, le=2.0, description="Movement speed multiplier")

    # Click settings
    click_delay_min_ms: int = Field(50, ge=0, description="Min delay before click")
    click_delay_max_ms: int = Field(200, ge=0, description="Max delay before click")


class SessionBehaviorSchema(BaseModel):
    """Session behavior and engagement configuration."""

    engagement_level: EngagementLevel = Field("active", description="Engagement intensity")

    # Dwell time (per page)
    dwell_time_min_sec: int = Field(15, ge=1, le=600, description="Min time on page (seconds)")
    dwell_time_max_sec: int = Field(60, ge=1, le=600, description="Max time on page (seconds)")

    # Navigation depth
    page_depth_min: int = Field(1, ge=1, le=50, description="Min pages to visit")
    page_depth_max: int = Field(5, ge=1, le=50, description="Max pages to visit")

    # Micro-breaks
    micro_breaks_enabled: bool = Field(True, description="Enable random pauses")
    break_probability: float = Field(0.15, ge=0, le=1, description="Chance of micro-break")
    break_min_sec: int = Field(1, ge=1, description="Min break duration")
    break_max_sec: int = Field(5, ge=1, description="Max break duration")

    # Persona from CoherenceEngine
    persona: (
        Literal["casual", "researcher", "shopper", "scanner", "power_user", "scroller"] | None
    ) = Field(None, description="User persona for behavior coherence")


class BehaviorModeSchema(BaseModel):
    """Complete behavior configuration for Step 5."""

    mode: BehaviorMode = Field("preset", description="Behavior decision mode")
    preset_name: str | None = Field("natural", description="Preset name when mode=preset")

    # Sub-configurations
    referrer: ReferrerConfigSchema = Field(default_factory=ReferrerConfigSchema)
    interaction: InteractionConfigSchema = Field(default_factory=InteractionConfigSchema)
    session: SessionBehaviorSchema = Field(default_factory=SessionBehaviorSchema)
    llm: LLMBehaviorConfig | None = Field(None, description="LLM config when mode=llm/hybrid")


# --- Platform Detection ---


class PlatformDetectRequest(BaseModel):
    """Request for platform detection."""

    url: str


class PlatformDetectResponse(BaseModel):
    """Response for platform detection."""

    platform: PlatformType
    detected: bool
    metadata: dict[str, str]


class PlatformConfigResponse(BaseModel):
    """Response with platform configuration schema."""

    platform: PlatformType
    config: dict[str, Any]
    schema_: dict[str, Any] = Field(alias="schema")


class AllPlatformsResponse(BaseModel):
    """Response with all platform configurations."""

    platforms: dict[PlatformType, dict[str, Any]]


# --- Metrics Schemas ---


class MetricsResponse(BaseModel):
    """Dashboard metrics response."""

    timestamp: datetime
    uptime_seconds: float | None

    # Tasks
    tasks_pending: int = 0
    tasks_running: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_per_minute: float = 0.0

    # Proxies
    proxies_total: int = 0
    proxies_healthy: int = 0
    proxies_failed: int = 0

    # Sessions
    sessions_active: int = 0
    pages_visited: int = 0

    # Workers
    workers_active: int = 0
    workers_total: int = 0


# --- WebSocket Event ---


class WebSocketEvent(BaseModel):
    """WebSocket event message."""

    type: str
    task_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Presets ---


class ConfigPreset(BaseModel):
    """Configuration preset."""

    name: str
    description: str
    platform: PlatformType
    config: dict[str, Any]


PRESETS: dict[str, ConfigPreset] = {
    "stealth": ConfigPreset(
        name="Stealth",
        description="Maximum anti-detection, slower but safer",
        platform="generic",
        config={
            "skip_probability": 0.35,
            "videos_per_session_min": 5,
            "videos_per_session_max": 15,
            "swipe_speed_min": 500,
            "swipe_speed_max": 1200,
        },
    ),
    "normal": ConfigPreset(
        name="Normal",
        description="Balanced settings for typical use",
        platform="generic",
        config={
            "skip_probability": 0.25,
            "videos_per_session_min": 10,
            "videos_per_session_max": 25,
            "swipe_speed_min": 300,
            "swipe_speed_max": 800,
        },
    ),
    "fast": ConfigPreset(
        name="Fast",
        description="Speed-focused, higher detection risk",
        platform="generic",
        config={
            "skip_probability": 0.40,
            "videos_per_session_min": 15,
            "videos_per_session_max": 40,
            "swipe_speed_min": 200,
            "swipe_speed_max": 500,
        },
    ),
}


# --- Flow Recording Schemas ---

# Flow types
CheckpointType = Literal["navigation", "click", "input", "wait", "scroll", "external", "custom"]
FlowStatusType = Literal["draft", "ready", "disabled"]
VariationLevelType = Literal["low", "medium", "high"]
BrowserEngineType = Literal["patchright", "camoufox", "playwright"]


class TimingConfigSchema(BaseModel):
    """Timing configuration for a checkpoint."""

    min_delay: float = Field(0.5, ge=0, description="Minimum wait before checkpoint (seconds)")
    max_delay: float = Field(3.0, ge=0, description="Maximum wait before checkpoint (seconds)")
    timeout: float = Field(30.0, ge=1, description="Max time to achieve checkpoint")


class CheckpointCreate(BaseModel):
    """Schema for creating a checkpoint."""

    checkpoint_type: CheckpointType = Field("custom", description="Type of checkpoint")
    goal: str = Field(..., min_length=1, description="Natural language goal description")
    url_pattern: str | None = Field(None, description="Regex pattern for expected URL")
    element_description: str | None = Field(None, description="Description of target element")
    selector_hints: list[str] = Field(default_factory=list, description="CSS/XPath hints")
    input_value: str | None = Field(None, description="Value to input (for INPUT type)")
    timing: TimingConfigSchema = Field(default_factory=TimingConfigSchema)
    reference_screenshot: str | None = Field(None, description="Base64 encoded screenshot")


class CheckpointResponse(BaseModel):
    """Response schema for a checkpoint."""

    id: str
    checkpoint_type: CheckpointType
    goal: str
    url_pattern: str | None
    element_description: str | None
    selector_hints: list[str]
    input_value: str | None
    timing: TimingConfigSchema
    order: int
    created_at: datetime
    has_screenshot: bool = False


class FlowCreate(BaseModel):
    """Schema for creating a new flow."""

    name: str = Field(..., min_length=1, max_length=100, description="Flow name")
    description: str = Field("", max_length=500, description="Flow description")
    start_url: str = Field(..., description="Starting URL for the flow")
    tags: list[str] = Field(default_factory=list, description="Tags for organization")

    @field_validator("start_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class FlowUpdate(BaseModel):
    """Schema for updating a flow."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    summary_goal: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    status: FlowStatusType | None = None


class FlowResponse(BaseModel):
    """Response schema for a flow."""

    id: str
    name: str
    description: str
    status: FlowStatusType
    start_url: str
    checkpoints: list[CheckpointResponse]
    summary_goal: str
    recorded_with_browser: str
    created_at: datetime
    updated_at: datetime
    times_executed: int
    successful_executions: int
    success_rate: float
    checkpoint_count: int
    tags: list[str]


class FlowListItem(BaseModel):
    """Simplified flow info for list views."""

    id: str
    name: str
    description: str
    status: FlowStatusType
    start_url: str
    checkpoint_count: int
    success_rate: float
    times_executed: int
    updated_at: datetime
    tags: list[str]


class FlowListResponse(BaseModel):
    """Response for flow list."""

    flows: list[FlowListItem]
    total: int
    ready: int
    draft: int


class FlowExecuteRequest(BaseModel):
    """Request to execute a recorded flow."""

    browser_engine: BrowserEngineType = Field(
        "camoufox", description="Browser engine for replay (camoufox recommended)"
    )
    variation_level: VariationLevelType = Field(
        "medium", description="How much to deviate from recorded behavior"
    )
    workers: int = Field(1, ge=1, le=50, description="Number of concurrent workers")
    use_proxy: bool = Field(True, description="Use proxy for execution")
    proxy_pool: str | None = Field(None, description="Specific proxy pool to use")
    substitutions: dict[str, str] = Field(
        default_factory=dict, description="Variable substitutions for input values"
    )
    checkpoint_timeout: float = Field(60.0, ge=10, description="Timeout per checkpoint")
    capture_screenshots: bool = Field(False, description="Capture screenshots during execution")


class FlowExecutionResponse(BaseModel):
    """Response for flow execution."""

    execution_id: str
    flow_id: str
    status: Literal["started", "running", "completed", "failed"]
    browser_engine: str
    workers: int
    message: str


class FlowExecutionStatus(BaseModel):
    """Status of a flow execution."""

    execution_id: str
    flow_id: str
    success: bool
    started_at: datetime
    completed_at: datetime | None
    duration: float | None
    checkpoints_completed: int
    total_checkpoints: int
    progress: float
    failed_at_checkpoint: str | None
    error: str | None
    browser_engine: str
    proxy_used: str | None


class RecordingStealthConfig(BaseModel):
    """Stealth configuration for recording sessions."""

    use_proxy: bool = Field(False, description="Route through proxy to hide real IP")
    use_fingerprint: bool = Field(False, description="Use random browser fingerprint")
    block_webrtc: bool = Field(True, description="Block WebRTC to prevent IP leak")
    canvas_noise: bool = Field(True, description="Add noise to canvas/WebGL fingerprinting")


class RecordingStartRequest(BaseModel):
    """Request to start recording a new flow."""

    name: str = Field(..., min_length=1, max_length=100, description="Flow name")
    start_url: str = Field(..., description="URL to navigate to for recording")
    description: str = Field("", max_length=500, description="Flow description")
    stealth: RecordingStealthConfig | None = Field(
        None, description="Optional stealth settings for recording"
    )

    @field_validator("start_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class RecordingStartResponse(BaseModel):
    """Response after starting recording."""

    flow_id: str
    status: Literal["recording"]
    message: str
    browser_launched: bool


class RecordingStopResponse(BaseModel):
    """Response after stopping recording."""

    flow_id: str
    status: FlowStatusType
    checkpoint_count: int
    message: str


class FlowSummaryResponse(BaseModel):
    """Summary statistics for flows."""

    total_flows: int
    ready: int
    draft: int
    disabled: int
    total_executions: int
    total_successful: int
    overall_success_rate: float
