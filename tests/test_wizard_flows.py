"""
Automated Wizard Flow Tests
Simulates user clicking through Steps 1-6 with different configurations
"""

import json
import random
from dataclasses import dataclass
from typing import Any

# Simulate the JavaScript state variables
wizard_state = {
    "currentWizardStep": 1,
    "currentPlatform": "generic",
    "currentMode": "batch",
    "selectedProxyProvider": "none",
    "currentUAMode": "dynamic",
    "currentFPMode": "dynamic",
    "currentBehaviorMode": "preset",
    "currentReferrerMode": "realistic",
    "currentMouseStyle": "natural",
    "currentEngagementLevel": "active",
    "currentLLMBehaviorProvider": "openai",
}

# Simulated form values
form_values = {}


def reset_state():
    """Reset to defaults like page load."""
    global wizard_state, form_values
    wizard_state = {
        "currentWizardStep": 1,
        "currentPlatform": "generic",
        "currentMode": "batch",
        "selectedProxyProvider": "none",
        "currentUAMode": "dynamic",
        "currentFPMode": "dynamic",
        "currentBehaviorMode": "preset",
        "currentReferrerMode": "realistic",
        "currentMouseStyle": "natural",
        "currentEngagementLevel": "active",
        "currentLLMBehaviorProvider": "openai",
    }
    form_values = {
        "url-input": "",
        "wizard-proxy-rotation": "per_request",
        "wizard-proxy-country": "",
        "wizard-proxy-session": "rotating",
        "wizard-tor-port": "9050",
        "wizard-tor-rotation": "per_session",
        "ua-dynamic-browser": "chrome",
        "ua-dynamic-os": "windows",
        "ua-dynamic-pool-size": "1000",
        "fp-dynamic-browser": "chrome",
        "fp-dynamic-os": "windows",
        "fp-dynamic-pool-size": "1000",
        "referrer-preset": "realistic",
        "ref-direct": "45",
        "ref-google": "25",
        "ref-social": "12",
        "ref-referral": "8",
        "ref-email": "5",
        "ref-ai": "2",
        "ref-variance": "10",
        "scroll-behavior": "smooth",
        "mouse-tremor": "15",
        "mouse-overshoot": "15",
        "mouse-speed": "100",
        "dwell-min": "15",
        "dwell-max": "60",
        "depth-min": "1",
        "depth-max": "5",
        "llm-model": "gpt-4o",
        "llm-personality": "casual",
        "llm-frequency": "key",
        "llm-temperature": "3",
        "workers": "5",
        "repeat": "1",
        "browser-engine": "patchright",
        "headless": True,
        "micro-breaks": True,
        "llm-vision": False,
    }


# ============ SIMULATE USER ACTIONS ============

def set_url(url: str):
    """Step 1: Enter URL."""
    form_values["url-input"] = url
    # Auto-detect platform
    if "tiktok.com" in url:
        wizard_state["currentPlatform"] = "tiktok"
    elif "instagram.com" in url:
        wizard_state["currentPlatform"] = "instagram"
    elif "youtube.com" in url:
        wizard_state["currentPlatform"] = "youtube"
    elif "dextools.io" in url:
        wizard_state["currentPlatform"] = "dextools"
    else:
        wizard_state["currentPlatform"] = "generic"


def set_proxy_provider(provider: str, **kwargs):
    """Step 2: Select proxy provider."""
    wizard_state["selectedProxyProvider"] = provider
    if "country" in kwargs:
        form_values["wizard-proxy-country"] = kwargs["country"]
    if "rotation" in kwargs:
        form_values["wizard-proxy-rotation"] = kwargs["rotation"]


def set_ua_mode(mode: str, **kwargs):
    """Step 3: Select UA mode."""
    wizard_state["currentUAMode"] = mode
    if "browser" in kwargs:
        form_values["ua-dynamic-browser"] = kwargs["browser"]
    if "os" in kwargs:
        form_values["ua-dynamic-os"] = kwargs["os"]
    if "pool_size" in kwargs:
        form_values["ua-dynamic-pool-size"] = str(kwargs["pool_size"])


def set_fp_mode(mode: str, **kwargs):
    """Step 4: Select fingerprint mode."""
    wizard_state["currentFPMode"] = mode
    if "browser" in kwargs:
        form_values["fp-dynamic-browser"] = kwargs["browser"]
    if "os" in kwargs:
        form_values["fp-dynamic-os"] = kwargs["os"]


def set_behavior_mode(mode: str):
    """Step 5: Select behavior mode."""
    wizard_state["currentBehaviorMode"] = mode


def set_referrer_mode(mode: str, **kwargs):
    """Step 5: Select referrer mode."""
    wizard_state["currentReferrerMode"] = mode
    if mode == "custom":
        for key in ["direct", "google", "social", "referral", "email", "ai"]:
            if key in kwargs:
                form_values[f"ref-{key}"] = str(kwargs[key])


def set_mouse_style(style: str):
    """Step 5: Select mouse style."""
    wizard_state["currentMouseStyle"] = style


def set_engagement(level: str, **kwargs):
    """Step 5: Select engagement level."""
    wizard_state["currentEngagementLevel"] = level
    if "dwell_min" in kwargs:
        form_values["dwell-min"] = str(kwargs["dwell_min"])
    if "dwell_max" in kwargs:
        form_values["dwell-max"] = str(kwargs["dwell_max"])


def set_llm_provider(provider: str, **kwargs):
    """Step 5: Select LLM provider."""
    wizard_state["currentLLMBehaviorProvider"] = provider
    if "model" in kwargs:
        form_values["llm-model"] = kwargs["model"]
    if "personality" in kwargs:
        form_values["llm-personality"] = kwargs["personality"]


def set_execution(mode: str = "batch", **kwargs):
    """Step 6: Set execution options."""
    wizard_state["currentMode"] = mode
    if "workers" in kwargs:
        form_values["workers"] = str(kwargs["workers"])
    if "repeat" in kwargs:
        form_values["repeat"] = str(kwargs["repeat"])
    if "browser" in kwargs:
        form_values["browser-engine"] = kwargs["browser"]
    if "headless" in kwargs:
        form_values["headless"] = kwargs["headless"]


# ============ COLLECT CONFIG (mirrors JS collectWizardConfig) ============

def collect_wizard_config() -> dict[str, Any]:
    """Simulate collectWizardConfig() from app.js."""
    use_proxies = wizard_state["selectedProxyProvider"] != "none"
    use_ua = wizard_state["currentUAMode"] != "none"
    use_fp = wizard_state["currentFPMode"] != "none"

    behavior_mode = wizard_state["currentBehaviorMode"]
    include_llm = behavior_mode in ("llm", "hybrid")

    return {
        # Target
        "url": form_values.get("url-input", ""),
        "platform": wizard_state["currentPlatform"],

        # Proxies
        "use_proxies": use_proxies,
        "proxy_provider": wizard_state["selectedProxyProvider"],
        "proxy_rotation": form_values.get("wizard-proxy-rotation", "per_request"),
        "proxy_country": form_values.get("wizard-proxy-country") or None,
        "proxy_session_type": form_values.get("wizard-proxy-session", "rotating"),
        "tor_port": int(form_values.get("wizard-tor-port", 9050)),
        "tor_rotation": form_values.get("wizard-tor-rotation", "per_session"),

        # User Agents
        "use_user_agents": use_ua,
        "user_agent_mode": wizard_state["currentUAMode"],
        "user_agent_browser": form_values.get("ua-dynamic-browser", "chrome"),
        "user_agent_os": form_values.get("ua-dynamic-os", "windows"),
        "user_agent_pool_size": int(form_values.get("ua-dynamic-pool-size", 1000)),

        # Fingerprints
        "use_fingerprints": use_fp,
        "fingerprint_mode": wizard_state["currentFPMode"],
        "fingerprint_browser": form_values.get("fp-dynamic-browser", "chrome"),
        "fingerprint_os": form_values.get("fp-dynamic-os", "windows"),
        "fingerprint_pool_size": int(form_values.get("fp-dynamic-pool-size", 1000)),

        # Behavior
        "behavior": {
            "mode": behavior_mode,
            "referrer": {
                "mode": wizard_state["currentReferrerMode"],
                "preset": form_values.get("referrer-preset", "realistic"),
                "direct_weight": int(form_values.get("ref-direct", 45)),
                "google_weight": int(form_values.get("ref-google", 25)),
                "social_weight": int(form_values.get("ref-social", 12)),
                "referral_weight": int(form_values.get("ref-referral", 8)),
                "email_weight": int(form_values.get("ref-email", 5)),
                "ai_search_weight": int(form_values.get("ref-ai", 2)),
                "variance_percent": int(form_values.get("ref-variance", 10)),
            },
            "interaction": {
                "mouse_style": wizard_state["currentMouseStyle"],
                "scroll_behavior": form_values.get("scroll-behavior", "smooth"),
                "tremor_amplitude": int(form_values.get("mouse-tremor", 15)) / 10,
                "overshoot_probability": int(form_values.get("mouse-overshoot", 15)) / 100,
                "speed_multiplier": int(form_values.get("mouse-speed", 100)) / 100,
            },
            "session": {
                "engagement_level": wizard_state["currentEngagementLevel"],
                "dwell_time_min_sec": int(form_values.get("dwell-min", 15)),
                "dwell_time_max_sec": int(form_values.get("dwell-max", 60)),
                "depth_min": int(form_values.get("depth-min", 1)),
                "depth_max": int(form_values.get("depth-max", 5)),
                "micro_breaks_enabled": form_values.get("micro-breaks", True),
            },
            "llm": {
                "provider": wizard_state["currentLLMBehaviorProvider"],
                "model": form_values.get("llm-model", "gpt-4o"),
                "personality": form_values.get("llm-personality", "casual"),
                "decision_frequency": form_values.get("llm-frequency", "key"),
                "vision_enabled": form_values.get("llm-vision", False),
                "temperature": int(form_values.get("llm-temperature", 3)) / 10,
            } if include_llm else None,
        },

        # Execution
        "mode": wizard_state["currentMode"],
        "workers": int(form_values.get("workers", 5)) if wizard_state["currentMode"] == "batch" else 1,
        "repeat": int(form_values.get("repeat", 1)),
        "headless": form_values.get("headless", True),
        "browser_engine": form_values.get("browser-engine", "patchright"),
    }


# ============ TEST FLOWS ============

@dataclass
class FlowResult:
    name: str
    config: dict
    passed: bool
    error: str | None = None


def validate_config(config: dict) -> tuple[bool, str | None]:
    """Validate config matches expected structure."""
    try:
        from ghoststorm.api.schemas import TaskCreate

        # Build payload like startTask() does
        payload = {
            "url": config["url"],
            "platform": config["platform"],
            "mode": config["mode"],
            "workers": config["workers"],
            "repeat": config["repeat"],
            "config": {
                "use_proxies": config["use_proxies"],
                "proxy_provider": config["proxy_provider"],
                "use_user_agents": config["use_user_agents"],
                "use_fingerprints": config["use_fingerprints"],
                "behavior": config["behavior"],
                "headless": config["headless"],
                "browser_engine": config["browser_engine"],
            },
            "behavior": config["behavior"],
        }

        task = TaskCreate(**payload)
        return True, None
    except Exception as e:
        return False, str(e)


def run_flow(name: str, steps: callable) -> FlowResult:
    """Run a test flow and validate."""
    reset_state()
    steps()
    config = collect_wizard_config()
    passed, error = validate_config(config)
    return FlowResult(name=name, config=config, passed=passed, error=error)


# ============ DEFINE TEST FLOWS ============

def flow_tiktok_full_stealth():
    """TikTok with all stealth options maxed."""
    set_url("https://www.tiktok.com/@username/video/123456")
    set_proxy_provider("decodo", country="us", rotation="per_request")
    set_ua_mode("dynamic", browser="chrome", os="windows", pool_size=2000)
    set_fp_mode("dynamic", browser="chrome", os="windows")
    set_behavior_mode("hybrid")
    set_referrer_mode("social_viral")
    set_mouse_style("natural")
    set_engagement("active", dwell_min=30, dwell_max=120)
    set_llm_provider("openai", model="gpt-4o", personality="casual")
    set_execution("batch", workers=10, repeat=5, browser="patchright")


def flow_instagram_tor_anonymous():
    """Instagram via Tor, maximum anonymity."""
    set_url("https://www.instagram.com/reel/ABC123")
    set_proxy_provider("tor")
    set_ua_mode("dynamic", browser="firefox", os="linux")
    set_fp_mode("dynamic", browser="firefox", os="linux")
    set_behavior_mode("preset")
    set_referrer_mode("none")
    set_mouse_style("slow")
    set_engagement("passive", dwell_min=5, dwell_max=15)
    set_execution("batch", workers=3, repeat=10, browser="camoufox")


def flow_youtube_ai_driven():
    """YouTube with full LLM control."""
    set_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    set_proxy_provider("brightdata", country="gb", rotation="per_session")
    set_ua_mode("dynamic", browser="chrome", os="macos")
    set_fp_mode("dynamic", browser="chrome", os="macos")
    set_behavior_mode("llm")
    set_referrer_mode("search_heavy")
    set_mouse_style("confident")
    set_engagement("deep", dwell_min=60, dwell_max=300)
    set_llm_provider("anthropic", model="claude-3-opus", personality="researcher")
    set_execution("batch", workers=5, repeat=3, browser="patchright")


def flow_dextools_debug():
    """DEXTools in debug mode for testing."""
    set_url("https://www.dextools.io/app/en/pairs")
    set_proxy_provider("none")
    set_ua_mode("none")
    set_fp_mode("none")
    set_behavior_mode("preset")
    set_referrer_mode("realistic")
    set_mouse_style("fast")
    set_engagement("active")
    set_execution("debug", headless=False)


def flow_generic_ollama_local():
    """Generic site with local Ollama LLM."""
    set_url("https://example.com/products")
    set_proxy_provider("file")
    set_ua_mode("dynamic", browser="edge", os="windows")
    set_fp_mode("dynamic", browser="edge", os="windows")
    set_behavior_mode("hybrid")
    set_referrer_mode("brand_focused")
    set_mouse_style("nervous")
    set_engagement("active", dwell_min=10, dwell_max=45)
    set_llm_provider("ollama", model="llama3", personality="shopper")
    set_execution("batch", workers=8, repeat=2, browser="playwright")


def flow_custom_referrer_mix():
    """Custom referrer weights for specific campaign."""
    set_url("https://mysite.com/landing")
    set_proxy_provider("oxylabs", country="de", rotation="per_page")
    set_ua_mode("dynamic", browser="chrome", os="windows")
    set_fp_mode("dynamic")
    set_behavior_mode("preset")
    set_referrer_mode("custom", direct=20, google=40, social=25, referral=10, email=3, ai=2)
    set_mouse_style("random")
    set_engagement("active")
    set_execution("batch", workers=15, repeat=1, browser="patchright")


def flow_minimal_config():
    """Bare minimum - just URL."""
    set_url("https://test.com")
    # Everything else stays default


def flow_everything_enabled():
    """Every option enabled and customized."""
    set_url("https://www.tiktok.com/@maxtest")
    set_proxy_provider("decodo", country="jp", rotation="per_request")
    set_ua_mode("dynamic", browser="chrome", os="android", pool_size=5000)
    set_fp_mode("dynamic", browser="chrome", os="android")
    set_behavior_mode("hybrid")
    set_referrer_mode("custom", direct=30, google=30, social=20, referral=10, email=5, ai=5)
    set_mouse_style("confident")
    set_engagement("deep", dwell_min=120, dwell_max=600)
    set_llm_provider("openai", model="gpt-4-turbo", personality="influencer")
    set_execution("batch", workers=50, repeat=100, browser="patchright", headless=True)


# ============ MAIN TEST RUNNER ============

def run_all_flows():
    """Run all test flows and report results."""
    flows = [
        ("TikTok Full Stealth", flow_tiktok_full_stealth),
        ("Instagram Tor Anonymous", flow_instagram_tor_anonymous),
        ("YouTube AI Driven", flow_youtube_ai_driven),
        ("DEXTools Debug", flow_dextools_debug),
        ("Generic Ollama Local", flow_generic_ollama_local),
        ("Custom Referrer Mix", flow_custom_referrer_mix),
        ("Minimal Config", flow_minimal_config),
        ("Everything Enabled", flow_everything_enabled),
    ]

    results = []
    print("\n" + "=" * 60)
    print("  WIZARD FLOW AUTOMATION TESTS")
    print("=" * 60 + "\n")

    for name, flow_func in flows:
        result = run_flow(name, flow_func)
        results.append(result)

        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{status}  {name}")

        if not result.passed:
            print(f"       Error: {result.error}")
        else:
            # Print key config summary
            c = result.config
            print(f"       URL: {c['url'][:40]}...")
            print(f"       Proxy: {c['proxy_provider']} | UA: {c['user_agent_mode']} | FP: {c['fingerprint_mode']}")
            print(f"       Behavior: {c['behavior']['mode']} | Mouse: {c['behavior']['interaction']['mouse_style']}")
            print(f"       Workers: {c['workers']} x {c['repeat']} = {c['workers'] * c['repeat']} sessions")
        print()

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("=" * 60)
    print(f"  RESULTS: {passed}/{total} flows passed")
    print("=" * 60)

    if passed == total:
        print("\n  ✓ ALL FLOWS VALIDATED SUCCESSFULLY\n")
    else:
        print("\n  ✗ SOME FLOWS FAILED - CHECK ERRORS ABOVE\n")
        for r in results:
            if not r.passed:
                print(f"    - {r.name}: {r.error}")

    return passed == total


def run_random_combinations(count: int = 20):
    """Generate and test random configuration combinations."""
    print("\n" + "=" * 60)
    print(f"  RANDOM COMBINATION TESTS ({count} flows)")
    print("=" * 60 + "\n")

    urls = [
        "https://www.tiktok.com/@random/video/123",
        "https://www.instagram.com/reel/XYZ",
        "https://www.youtube.com/watch?v=abc123",
        "https://dextools.io/app/pairs",
        "https://example.com/page",
        "https://mysite.io/landing",
    ]

    proxy_providers = ["none", "decodo", "brightdata", "oxylabs", "tor", "file"]
    proxy_countries = [None, "us", "gb", "de", "jp", "fr"]
    ua_modes = ["none", "dynamic", "file"]
    fp_modes = ["none", "dynamic", "file"]
    behavior_modes = ["preset", "llm", "hybrid"]
    referrer_modes = ["realistic", "search_heavy", "social_viral", "brand_focused", "custom", "none"]
    mouse_styles = ["natural", "fast", "slow", "nervous", "confident", "random"]
    engagement_levels = ["passive", "active", "deep"]
    llm_providers = ["openai", "anthropic", "ollama"]
    browsers = ["patchright", "playwright", "camoufox"]
    exec_modes = ["batch", "debug"]

    passed = 0
    failed = 0

    for i in range(count):
        reset_state()

        # Random selections
        url = random.choice(urls)
        proxy = random.choice(proxy_providers)
        country = random.choice(proxy_countries) if proxy not in ["none", "tor", "file"] else None
        ua = random.choice(ua_modes)
        fp = random.choice(fp_modes)
        behavior = random.choice(behavior_modes)
        referrer = random.choice(referrer_modes)
        mouse = random.choice(mouse_styles)
        engage = random.choice(engagement_levels)
        llm = random.choice(llm_providers)
        browser = random.choice(browsers)
        exec_mode = random.choice(exec_modes)
        workers = random.randint(1, 50) if exec_mode == "batch" else 1
        repeat = random.randint(1, 100)

        # Apply settings
        set_url(url)
        set_proxy_provider(proxy, country=country) if country else set_proxy_provider(proxy)
        set_ua_mode(ua)
        set_fp_mode(fp)
        set_behavior_mode(behavior)
        set_referrer_mode(referrer)
        set_mouse_style(mouse)
        set_engagement(engage)
        set_llm_provider(llm)
        set_execution(exec_mode, workers=workers, repeat=repeat, browser=browser)

        # Validate
        config = collect_wizard_config()
        valid, error = validate_config(config)

        combo = f"[{proxy[:3]}|{ua[:3]}|{fp[:3]}|{behavior[:3]}|{mouse[:3]}|{browser[:4]}]"

        if valid:
            passed += 1
            print(f"✓ #{i+1:02d} {combo} → {workers}x{repeat}={workers*repeat} sessions")
        else:
            failed += 1
            print(f"✗ #{i+1:02d} {combo} ERROR: {error}")

    print("\n" + "-" * 60)
    print(f"  Random tests: {passed}/{count} passed")

    return failed == 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")

    # Run defined flows
    flows_ok = run_all_flows()

    # Run random combinations
    random_ok = run_random_combinations(30)

    print("\n" + "=" * 60)
    if flows_ok and random_ok:
        print("  ✓ ALL TESTS PASSED - PIPELINE IS SOLID")
    else:
        print("  ✗ SOME TESTS FAILED")
    print("=" * 60 + "\n")

    sys.exit(0 if (flows_ok and random_ok) else 1)
