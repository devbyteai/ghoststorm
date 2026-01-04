"""
Flow Recording Example

Record browser actions and replay them with variation.
"""
import asyncio
from ghoststorm.core.flow import FlowRecorder, FlowExecutor
from ghoststorm.core.models.config import GhostStormConfig


async def record_flow():
    """Record a new flow interactively."""
    config = GhostStormConfig(headless=False)
    recorder = FlowRecorder(config)
    
    # Start recording - browser opens for interaction
    flow = await recorder.start(
        name="example_flow",
        start_url="https://example.com",
    )
    
    print("Browser opened. Interact with the page.")
    print("Press Ctrl+C when done to save the flow.")
    
    try:
        await asyncio.Event().wait()  # Wait forever
    except KeyboardInterrupt:
        pass
    
    # Save the recorded flow
    await recorder.stop()
    print(f"Flow saved: {flow.id}")
    return flow


async def replay_flow(flow_id: str):
    """Replay a recorded flow with variation."""
    config = GhostStormConfig(headless=True)
    executor = FlowExecutor(config)
    
    result = await executor.execute(
        flow_id=flow_id,
        variation_level="medium",  # low, medium, high
        use_llm=True,  # Enable LLM for intelligent variation
    )
    
    print(f"Flow completed: {result.status}")
    print(f"Checkpoints reached: {len(result.checkpoints)}")


async def main():
    # Record a new flow
    flow = await record_flow()
    
    # Replay it 3 times with variation
    for i in range(3):
        print(f"\nReplay {i+1}:")
        await replay_flow(flow.id)


if __name__ == "__main__":
    asyncio.run(main())
