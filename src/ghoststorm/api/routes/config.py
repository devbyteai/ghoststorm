"""Configuration API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ghoststorm.core.models.config import Config
from ghoststorm.api.schemas import (
    PRESETS,
    AllPlatformsResponse,
    BehaviorConfigSchema,
    DEXToolsConfigSchema,
    EngineConfigSchema,
    GenericConfigSchema,
    InstagramConfigSchema,
    PlatformConfigResponse,
    PlatformType,
    TikTokConfigSchema,
    YouTubeConfigSchema,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

# Platform config schemas
PLATFORM_CONFIGS: dict[PlatformType, type] = {
    "tiktok": TikTokConfigSchema,
    "instagram": InstagramConfigSchema,
    "youtube": YouTubeConfigSchema,
    "dextools": DEXToolsConfigSchema,
    "generic": GenericConfigSchema,
}


def _get_schema_info(schema_class: type) -> dict[str, Any]:
    """Extract schema info including field descriptions and defaults."""
    schema = schema_class.model_json_schema()
    defaults = {}

    # Get default values
    for field_name, field_info in schema_class.model_fields.items():
        if field_info.default is not None:
            defaults[field_name] = field_info.default
        elif field_info.default_factory is not None:
            defaults[field_name] = field_info.default_factory()

    return {
        "schema": schema,
        "defaults": defaults,
        "fields": list(schema_class.model_fields.keys()),
    }


@router.get("/platforms", response_model=AllPlatformsResponse)
async def list_platforms() -> AllPlatformsResponse:
    """List all supported platforms with their default configurations."""
    platforms = {}

    for platform, config_class in PLATFORM_CONFIGS.items():
        info = _get_schema_info(config_class)
        platforms[platform] = {
            "defaults": info["defaults"],
            "fields": info["fields"],
            "description": config_class.__doc__ or f"{platform.title()} configuration",
        }

    return AllPlatformsResponse(platforms=platforms)


@router.get("/platforms/{platform}", response_model=PlatformConfigResponse)
async def get_platform_config(platform: PlatformType) -> PlatformConfigResponse:
    """Get configuration schema and defaults for a specific platform."""
    if platform not in PLATFORM_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown platform: {platform}",
        )

    config_class = PLATFORM_CONFIGS[platform]
    info = _get_schema_info(config_class)

    return PlatformConfigResponse(
        platform=platform,
        config=info["defaults"],
        schema=info["schema"],
    )


@router.get("/engine")
async def get_engine_config() -> dict[str, Any]:
    """Get core engine configuration options."""
    info = _get_schema_info(EngineConfigSchema)
    return {
        "config": info["defaults"],
        "schema": info["schema"],
        "description": "Core engine configuration for browser, proxies, and execution",
    }


@router.get("/behavior")
async def get_behavior_config() -> dict[str, Any]:
    """Get behavior simulation configuration options."""
    info = _get_schema_info(BehaviorConfigSchema)
    return {
        "config": info["defaults"],
        "schema": info["schema"],
        "description": "Human behavior simulation settings",
    }


@router.get("/presets")
async def list_presets() -> dict[str, list[dict[str, Any]]]:
    """List available configuration presets."""
    return {
        "presets": [
            {
                "id": preset_id,
                "name": preset.name,
                "description": preset.description,
                "config": preset.config,
            }
            for preset_id, preset in PRESETS.items()
        ]
    }


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str) -> dict[str, Any]:
    """Get a specific preset configuration."""
    if preset_id not in PRESETS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset not found: {preset_id}",
        )

    preset = PRESETS[preset_id]
    return {
        "id": preset_id,
        "name": preset.name,
        "description": preset.description,
        "config": preset.config,
    }


@router.get("/all")
async def get_all_config() -> dict[str, Any]:
    """Get all configuration options for all platforms."""
    result = {
        "platforms": {},
        "engine": _get_schema_info(EngineConfigSchema),
        "behavior": _get_schema_info(BehaviorConfigSchema),
        "presets": [
            {
                "id": preset_id,
                "name": preset.name,
                "description": preset.description,
                "config": preset.config,
            }
            for preset_id, preset in PRESETS.items()
        ],
    }

    for platform, config_class in PLATFORM_CONFIGS.items():
        result["platforms"][platform] = _get_schema_info(config_class)

    return result


# User config file path - use project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent  # src/ghoststorm/api/routes -> project root
USER_CONFIG_PATH = _PROJECT_ROOT / "config" / "user_config.yaml"


@router.get("/current")
async def get_current_config() -> dict[str, Any]:
    """Get current user configuration."""
    try:
        if USER_CONFIG_PATH.exists():
            config = Config.from_yaml(USER_CONFIG_PATH)
        else:
            config = Config()  # Use defaults
        return config.to_dict()
    except Exception as e:
        logger.error("Failed to load config", error=str(e))
        return Config().to_dict()


@router.post("/save")
async def save_config(settings: dict[str, Any]) -> dict[str, str]:
    """Save user configuration to YAML file."""
    try:
        # Merge with defaults to ensure all fields exist
        default_config = Config()
        default_dict = default_config.to_dict()

        # Deep merge user settings into defaults
        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                elif value is not None:
                    result[key] = value
            return result

        merged = deep_merge(default_dict, settings)
        config = Config.from_dict(merged)
        config.to_yaml(USER_CONFIG_PATH)

        logger.info("Configuration saved", path=str(USER_CONFIG_PATH))
        return {"status": "saved", "path": str(USER_CONFIG_PATH)}

    except Exception as e:
        logger.error("Failed to save config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}",
        )


@router.post("/reset")
async def reset_config() -> dict[str, str]:
    """Reset configuration to defaults."""
    try:
        if USER_CONFIG_PATH.exists():
            USER_CONFIG_PATH.unlink()
        return {"status": "reset", "message": "Configuration reset to defaults"}
    except Exception as e:
        logger.error("Failed to reset config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset configuration: {str(e)}",
        )


# =============================================================================
# DEXTools Specific Endpoints
# =============================================================================


class DEXToolsSelectorTestRequest(BaseModel):
    """Request for DEXTools selector test."""

    pair_url: str = "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7"
    browser_engine: str = "patchright"
    headless: bool = True
    timeout_s: float = 30.0


class DEXToolsSelectorTestResponse(BaseModel):
    """Response from DEXTools selector test."""

    status: str  # ready, partial, broken, error
    page_loads: bool
    chart_visible: bool
    social_links_found: int
    tabs_found: int
    search_found: bool
    errors: list[str]
    recommendations: list[str]


@router.post("/dextools/test-selectors", response_model=DEXToolsSelectorTestResponse)
async def test_dextools_selectors(
    request: DEXToolsSelectorTestRequest,
) -> DEXToolsSelectorTestResponse:
    """Test DEXTools selectors against current UI.

    Use this to verify selectors still work after DEXTools updates their UI.
    Returns status and recommendations for fixing broken selectors.
    """
    try:
        from ghoststorm.plugins.automation.dextools import (
            DEXToolsAutomation,
            DEXToolsConfig,
        )

        # Try to launch browser and test
        try:
            from patchright.async_api import async_playwright
        except ImportError:
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                return DEXToolsSelectorTestResponse(
                    status="error",
                    page_loads=False,
                    chart_visible=False,
                    social_links_found=0,
                    tabs_found=0,
                    search_found=False,
                    errors=["No browser engine available (patchright or playwright required)"],
                    recommendations=["Install patchright: pip install patchright"],
                )

        automation = DEXToolsAutomation(DEXToolsConfig())

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=request.headless)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                results = await automation.test_selectors(page, request.pair_url)
            finally:
                await page.close()
                await context.close()
                await browser.close()

        # Generate recommendations
        recommendations = []
        if not results.get("page_loads"):
            recommendations.append("Page failed to load - check if DEXTools is accessible")
        if not results.get("chart_visible"):
            recommendations.append("Chart not found - selector may need update")
        if results.get("social_links_found", 0) < 2:
            recommendations.append("Few social links found - some tokens may not have all links")
        if results.get("tabs_found", 0) == 0:
            recommendations.append("No tabs found - tab selector may need update")

        return DEXToolsSelectorTestResponse(
            status=results.get("status", "unknown"),
            page_loads=results.get("page_loads", False),
            chart_visible=results.get("chart_visible", False),
            social_links_found=results.get("social_links_found", 0),
            tabs_found=results.get("tabs_found", 0),
            search_found=results.get("search_found", False),
            errors=results.get("errors", []),
            recommendations=recommendations,
        )

    except Exception as e:
        logger.error("DEXTools selector test failed", error=str(e))
        return DEXToolsSelectorTestResponse(
            status="error",
            page_loads=False,
            chart_visible=False,
            social_links_found=0,
            tabs_found=0,
            search_found=False,
            errors=[str(e)],
            recommendations=["Check browser installation and network connectivity"],
        )


@router.get("/dextools/selectors")
async def get_dextools_selectors() -> dict[str, Any]:
    """Get current DEXTools selectors.

    Returns the CSS/XPath selectors used for DEXTools automation.
    Useful for debugging or manual updates.
    """
    from ghoststorm.plugins.automation.dextools import DEXToolsSelectors

    selectors = DEXToolsSelectors()
    return {
        "social_links": {
            "container": selectors.social_links_container,
            "twitter": selectors.social_link_twitter,
            "telegram": selectors.social_link_telegram,
            "discord": selectors.social_link_discord,
            "website": selectors.social_link_website,
        },
        "xpath_fallbacks": {
            "social_link_1": selectors.social_link_1_xpath,
            "social_link_2": selectors.social_link_2_xpath,
            "social_link_3": selectors.social_link_3_xpath,
            "social_link_4": selectors.social_link_4_xpath,
        },
        "chart": {
            "container": selectors.chart_container,
            "tabs": selectors.chart_tabs,
        },
        "ui_elements": {
            "tab_buttons": selectors.tab_buttons,
            "info_button": selectors.info_button,
            "modal_container": selectors.modal_container,
            "modal_close": selectors.modal_close,
            "search_input": selectors.search_input,
            "search_results": selectors.search_results,
            "favorite_button": selectors.favorite_button,
        },
        "update_instructions": (
            "To update selectors: "
            "1. Open DEXTools pair page in browser, "
            "2. Right-click element → Inspect, "
            "3. Update selectors in src/ghoststorm/plugins/automation/dextools.py"
        ),
    }


@router.get("/dextools/behavior-weights")
async def get_dextools_behavior_weights() -> dict[str, Any]:
    """Get DEXTools visitor behavior distribution weights.

    Shows how visitors are distributed across behavior types in 'realistic' mode.
    """
    from ghoststorm.plugins.automation.dextools import BEHAVIOR_WEIGHTS, VisitorBehavior

    return {
        "mode": "realistic",
        "description": "Distribution of visitor behavior types",
        "weights": {
            behavior.value: weight
            for behavior, weight in BEHAVIOR_WEIGHTS.items()
        },
        "explanations": {
            "passive": "60% - View page, light scroll, leave (most common real user behavior)",
            "light": "30% - View + 1 interaction (social click or tab)",
            "engaged": "10% - Multiple interactions (rare but valuable for trending)",
        },
    }
