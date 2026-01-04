"""
Basic URL Visit Example

Simple example showing how to visit URLs with GhostStorm.
"""
import asyncio
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig
from ghoststorm.core.models.config import GhostStormConfig


async def main():
    # Initialize with default config
    config = GhostStormConfig()
    orchestrator = Orchestrator(config)
    
    await orchestrator.start()
    
    try:
        # Create a simple visit task
        task = Task(
            url="https://example.com",
            task_type=TaskType.VISIT,
            config=TaskConfig(
                human_simulation=True,
                scroll_page=True,
                dwell_time=(5.0, 15.0),  # Stay 5-15 seconds
            )
        )
        
        # Submit and wait for completion
        task_id = await orchestrator.submit_task(task)
        result = await orchestrator.wait_for_task(task_id)
        
        print(f"Task completed: {result.status}")
        print(f"Duration: {result.duration_ms}ms")
        
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
