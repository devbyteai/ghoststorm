"""
LLM-Powered Automation Example

Use AI to intelligently navigate and interact with websites.
"""
import asyncio
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig
from ghoststorm.core.models.config import GhostStormConfig
from ghoststorm.llm import OllamaProvider


async def main():
    # Configure LLM provider
    llm = OllamaProvider(
        base_url="http://localhost:11434",
        model="qwen2.5-coder:7b",
    )
    
    config = GhostStormConfig(
        llm_provider=llm,
        llm_mode="autonomous",  # off, assist, autonomous
        vision_mode="auto",  # off, auto, always
    )
    
    orchestrator = Orchestrator(config)
    await orchestrator.start()
    
    try:
        # Create an AI-driven task
        task = Task(
            url="https://news.ycombinator.com",
            task_type=TaskType.AUTONOMOUS,
            config=TaskConfig(
                goal="Find and click on the top story, then read the comments",
                max_steps=10,
                screenshot_each_step=True,
            )
        )
        
        result = await orchestrator.run_task(task)
        
        print(f"Task completed: {result.status}")
        print(f"Steps taken: {len(result.steps)}")
        for step in result.steps:
            print(f"  - {step.action}: {step.element}")
        
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
