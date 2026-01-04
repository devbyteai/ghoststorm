"""
Stealth Configuration Example

Configure anti-detection measures for maximum stealth.
"""
import asyncio
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig
from ghoststorm.core.models.config import GhostStormConfig
from ghoststorm.plugins.evasion import StealthConfig


async def main():
    # Configure stealth options
    stealth = StealthConfig(
        # Fingerprint randomization
        randomize_canvas=True,
        randomize_webgl=True,
        randomize_audio=True,
        
        # Leak prevention
        block_webrtc=True,
        prevent_dns_leak=True,
        disable_ipv6=True,
        
        # Automation detection
        hide_automation_indicators=True,
        spoof_navigator=True,
        realistic_plugins=True,
        
        # Timezone/locale
        timezone_spoof="auto",  # Match proxy location
        locale_spoof="auto",
    )
    
    config = GhostStormConfig(
        browser_engine="camoufox",  # Maximum stealth
        stealth_config=stealth,
        headless=True,
    )
    
    orchestrator = Orchestrator(config)
    await orchestrator.start()
    
    try:
        # Test on fingerprint detection sites
        test_sites = [
            "https://bot.sannysoft.com",
            "https://browserleaks.com/canvas",
            "https://ipleak.net",
        ]
        
        for url in test_sites:
            task = Task(
                url=url,
                task_type=TaskType.VISIT,
                config=TaskConfig(
                    screenshot=True,
                    dwell_time=(10.0, 15.0),
                )
            )
            
            result = await orchestrator.run_task(task)
            print(f"{url}: {result.status}")
            if result.screenshot:
                print(f"  Screenshot: {result.screenshot}")
        
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
