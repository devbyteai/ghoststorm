"""
Batch URL Visits Example

Visit multiple URLs concurrently with proxy rotation.
"""
import asyncio
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig
from ghoststorm.core.models.config import GhostStormConfig


async def main():
    config = GhostStormConfig(
        max_workers=5,
        headless=True,
    )
    orchestrator = Orchestrator(config)
    
    await orchestrator.start()
    
    try:
        # Create batch of tasks
        urls = [
            "https://example.com",
            "https://httpbin.org/get",
            "https://jsonplaceholder.typicode.com",
        ]
        
        tasks = [
            Task(
                url=url,
                task_type=TaskType.VISIT,
                config=TaskConfig(
                    human_simulation=True,
                    scroll_page=True,
                    dwell_time=(3.0, 8.0),
                )
            )
            for url in urls
        ]
        
        # Submit batch
        batch_id = await orchestrator.submit_batch(tasks)
        
        # Wait for all to complete
        results = await orchestrator.wait_for_batch(batch_id)
        
        print(f"Completed {len(results)} tasks")
        for result in results:
            print(f"  {result.url}: {result.status}")
        
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
