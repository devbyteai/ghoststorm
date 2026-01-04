"""
Proxy Rotation Example

Visit URLs with automatic proxy rotation.
"""
import asyncio
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig
from ghoststorm.core.models.config import GhostStormConfig
from ghoststorm.proxy import ProxyPool


async def main():
    # Load proxies from file
    proxy_pool = ProxyPool()
    await proxy_pool.load_from_file("proxies.txt")
    
    # Or add proxies programmatically
    # proxy_pool.add("http://user:pass@host:port")
    # proxy_pool.add("socks5://host:port")
    
    config = GhostStormConfig(
        proxy_pool=proxy_pool,
        proxy_rotation="round_robin",  # or "random", "weighted"
    )
    
    orchestrator = Orchestrator(config)
    await orchestrator.start()
    
    try:
        task = Task(
            url="https://httpbin.org/ip",
            task_type=TaskType.VISIT,
            config=TaskConfig(
                use_proxy=True,
            )
        )
        
        # Run 5 times, each with different proxy
        for i in range(5):
            result = await orchestrator.run_task(task)
            print(f"Visit {i+1}: IP shown on page (through proxy)")
        
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
