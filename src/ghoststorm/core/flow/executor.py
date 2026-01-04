"""Flow executor with LLM-driven replay and behavior variation."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

import structlog

from ghoststorm.core.models.flow import (
    Checkpoint,
    FlowExecutionConfig,
    FlowExecutionResult,
    RecordedFlow,
    VariationLevel,
)
from ghoststorm.core.flow.storage import FlowStorage, get_flow_storage

logger = structlog.get_logger(__name__)


@dataclass
class ExecutionContext:
    """Context for flow execution."""

    flow: RecordedFlow
    config: FlowExecutionConfig
    result: FlowExecutionResult
    browser: Any = None
    context: Any = None
    page: Any = None
    llm_controller: Any = None
    coherence_engine: Any = None
    on_checkpoint_start: Callable[[Checkpoint], None] | None = None
    on_checkpoint_complete: Callable[[Checkpoint, bool], None] | None = None
    on_progress: Callable[[float], None] | None = None


class FlowExecutor:
    """Executes recorded flows with LLM-driven variation."""

    def __init__(
        self,
        storage: FlowStorage | None = None,
    ) -> None:
        """Initialize flow executor.

        Args:
            storage: Flow storage instance.
        """
        self.storage = storage or get_flow_storage()
        self._active_executions: dict[str, ExecutionContext] = {}

        logger.info("FlowExecutor initialized")

    async def execute(
        self,
        flow_id: str,
        config: FlowExecutionConfig | None = None,
        *,
        on_checkpoint_start: Callable[[Checkpoint], None] | None = None,
        on_checkpoint_complete: Callable[[Checkpoint, bool], None] | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> FlowExecutionResult:
        """Execute a recorded flow.

        Args:
            flow_id: ID of the flow to execute.
            config: Execution configuration.
            on_checkpoint_start: Callback when checkpoint starts.
            on_checkpoint_complete: Callback when checkpoint completes.
            on_progress: Callback for progress updates.

        Returns:
            Execution result.
        """
        # Load flow
        flow = await self.storage.load(flow_id)
        if not flow:
            raise ValueError(f"Flow not found: {flow_id}")

        if not flow.checkpoints:
            raise ValueError(f"Flow has no checkpoints: {flow_id}")

        # Create config if not provided
        config = config or FlowExecutionConfig(flow_id=flow_id)
        config.flow_id = flow_id

        # Create result
        result = FlowExecutionResult(
            flow_id=flow_id,
            total_checkpoints=len(flow.checkpoints),
            browser_engine=config.browser_engine,
        )

        # Create execution context
        ctx = ExecutionContext(
            flow=flow,
            config=config,
            result=result,
            on_checkpoint_start=on_checkpoint_start,
            on_checkpoint_complete=on_checkpoint_complete,
            on_progress=on_progress,
        )

        self._active_executions[result.execution_id] = ctx

        try:
            # Initialize browser
            await self._init_browser(ctx)

            # Initialize LLM controller
            await self._init_llm_controller(ctx)

            # Initialize coherence engine for variation
            await self._init_coherence_engine(ctx)

            # Navigate to start URL
            await ctx.page.goto(flow.start_url, wait_until="domcontentloaded")

            # Execute each checkpoint
            for i, checkpoint in enumerate(flow.checkpoints):
                if ctx.on_checkpoint_start:
                    ctx.on_checkpoint_start(checkpoint)

                success = await self._execute_checkpoint(ctx, checkpoint)

                if ctx.on_checkpoint_complete:
                    ctx.on_checkpoint_complete(checkpoint, success)

                result.checkpoints_completed = i + 1

                if ctx.on_progress:
                    ctx.on_progress(result.progress)

                if not success:
                    result.failed_at_checkpoint = checkpoint.id
                    break

                # Add variation delay between checkpoints
                await self._add_variation_delay(ctx, checkpoint)

            # Determine final success
            result.success = result.checkpoints_completed == result.total_checkpoints
            result.complete(result.success)

            # Update flow stats
            await self.storage.update_execution_stats(flow_id, result.success)

            logger.info(
                "Flow execution completed",
                flow_id=flow_id,
                execution_id=result.execution_id,
                success=result.success,
                checkpoints_completed=result.checkpoints_completed,
                total=result.total_checkpoints,
            )

            return result

        except Exception as e:
            logger.error("Flow execution failed", error=str(e))
            result.complete(False, str(e))
            return result

        finally:
            # Cleanup
            await self._cleanup(ctx)
            del self._active_executions[result.execution_id]

    async def _init_browser(self, ctx: ExecutionContext) -> None:
        """Initialize browser based on config."""
        engine = ctx.config.browser_engine

        if engine == "patchright":
            from patchright.async_api import async_playwright

            playwright = await async_playwright().start()
            ctx.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            ctx.context = await ctx.browser.new_context(
                viewport={"width": 1280, "height": 800},
            )
            ctx.page = await ctx.context.new_page()

        elif engine == "camoufox":
            try:
                from camoufox.async_api import AsyncCamoufox

                ctx.browser = await AsyncCamoufox(headless=True).start()
                ctx.page = await ctx.browser.new_page()
                ctx.context = ctx.page.context
            except ImportError:
                # Fallback to patchright
                logger.warning("Camoufox not available, falling back to patchright")
                ctx.config.browser_engine = "patchright"
                await self._init_browser(ctx)

        elif engine == "playwright":
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            ctx.browser = await playwright.chromium.launch(headless=True)
            ctx.context = await ctx.browser.new_context(
                viewport={"width": 1280, "height": 800},
            )
            ctx.page = await ctx.context.new_page()

        else:
            raise ValueError(f"Unknown browser engine: {engine}")

        logger.debug("Browser initialized", engine=engine)

    async def _init_llm_controller(self, ctx: ExecutionContext) -> None:
        """Initialize LLM controller for autonomous execution."""
        try:
            from ghoststorm.core.llm.controller import (
                ControllerConfig,
                ControllerMode,
                LLMController,
            )
            from ghoststorm.core.llm.service import LLMService

            # Create LLM service
            llm_service = LLMService()

            # Create controller config based on variation level
            variation = ctx.config.variation_level
            config = ControllerConfig(
                mode=ControllerMode.AUTONOMOUS,
                max_steps=15,  # Steps per checkpoint
                step_delay=self._get_step_delay(variation),
                min_confidence=0.4,  # Lower threshold for more variation
                timeout_per_step=ctx.config.checkpoint_timeout / 10,
            )

            ctx.llm_controller = LLMController(llm_service, config=config)
            logger.debug("LLM controller initialized", variation=variation.value)

        except Exception as e:
            logger.warning("Failed to initialize LLM controller", error=str(e))
            ctx.llm_controller = None

    async def _init_coherence_engine(self, ctx: ExecutionContext) -> None:
        """Initialize coherence engine for behavior variation."""
        try:
            from ghoststorm.plugins.behavior.coherence_engine import (
                CoherenceEngine,
                UserPersona,
            )

            # Select random persona for variation
            personas = [
                UserPersona.CASUAL,
                UserPersona.RESEARCHER,
                UserPersona.SCANNER,
            ]
            persona = random.choice(personas)

            ctx.coherence_engine = CoherenceEngine(persona=persona)
            logger.debug("Coherence engine initialized", persona=persona.value)

        except Exception as e:
            logger.warning("Failed to initialize coherence engine", error=str(e))
            ctx.coherence_engine = None

    def _get_step_delay(self, variation: VariationLevel) -> float:
        """Get step delay based on variation level."""
        if variation == VariationLevel.LOW:
            return random.uniform(0.3, 0.6)
        elif variation == VariationLevel.MEDIUM:
            return random.uniform(0.5, 1.5)
        else:  # HIGH
            return random.uniform(1.0, 3.0)

    async def _execute_checkpoint(
        self,
        ctx: ExecutionContext,
        checkpoint: Checkpoint,
    ) -> bool:
        """Execute a single checkpoint using LLM.

        Args:
            ctx: Execution context.
            checkpoint: Checkpoint to execute.

        Returns:
            True if checkpoint was achieved.
        """
        logger.info(
            "Executing checkpoint",
            checkpoint_id=checkpoint.id,
            goal=checkpoint.goal,
            type=checkpoint.checkpoint_type.value,
        )

        try:
            # Build task description for LLM
            task = self._build_checkpoint_task(ctx, checkpoint)

            # Apply input substitutions
            task = self._apply_substitutions(task, ctx.config.substitutions)

            if ctx.llm_controller:
                # Use LLM AUTONOMOUS mode
                from ghoststorm.core.llm.controller import TaskResult

                result = await asyncio.wait_for(
                    ctx.llm_controller.execute_task(ctx.page, task),
                    timeout=ctx.config.checkpoint_timeout,
                )

                if result.success:
                    logger.debug(
                        "Checkpoint achieved via LLM",
                        steps=result.steps_taken,
                    )
                    return True
                else:
                    logger.warning(
                        "LLM failed to achieve checkpoint",
                        error=result.error,
                    )
                    # Fall through to fallback

            # Fallback: Simple execution without LLM
            return await self._execute_checkpoint_fallback(ctx, checkpoint)

        except asyncio.TimeoutError:
            logger.warning("Checkpoint timed out", checkpoint_id=checkpoint.id)
            ctx.result.error = f"Checkpoint timed out: {checkpoint.goal}"
            return False

        except Exception as e:
            logger.error("Checkpoint execution error", error=str(e))
            ctx.result.error = str(e)
            return False

    def _build_checkpoint_task(
        self,
        ctx: ExecutionContext,
        checkpoint: Checkpoint,
    ) -> str:
        """Build task description for LLM."""
        parts = [f"Goal: {checkpoint.goal}"]

        if checkpoint.element_description:
            parts.append(f"Target element: {checkpoint.element_description}")

        if checkpoint.input_value:
            parts.append(f"Input value: {checkpoint.input_value}")

        if checkpoint.selector_hints:
            hints = ", ".join(checkpoint.selector_hints)
            parts.append(f"Selector hints: {hints}")

        # Add variation instruction based on level
        variation = ctx.config.variation_level
        if variation == VariationLevel.LOW:
            parts.append("Execute efficiently with minimal variation.")
        elif variation == VariationLevel.MEDIUM:
            parts.append("Use natural browsing behavior with some variation in timing and approach.")
        else:  # HIGH
            parts.append(
                "Behave like a real human: take your time, maybe scroll around first, "
                "approach the goal indirectly with natural exploration."
            )

        return " ".join(parts)

    def _apply_substitutions(
        self,
        text: str,
        substitutions: dict[str, str],
    ) -> str:
        """Apply variable substitutions to text."""
        result = text
        for key, value in substitutions.items():
            result = result.replace(f"{{{key}}}", value)
        return result

    async def _execute_checkpoint_fallback(
        self,
        ctx: ExecutionContext,
        checkpoint: Checkpoint,
    ) -> bool:
        """Fallback checkpoint execution without LLM.

        Uses selector hints and simple heuristics.
        """
        try:
            checkpoint_type = checkpoint.checkpoint_type.value

            if checkpoint_type == "navigation":
                # Navigate to URL pattern if available
                if checkpoint.url_pattern:
                    await ctx.page.goto(checkpoint.url_pattern, wait_until="domcontentloaded")
                    return True

            elif checkpoint_type == "click":
                # Try selector hints
                for selector in checkpoint.selector_hints:
                    try:
                        await ctx.page.click(selector, timeout=5000)
                        return True
                    except Exception:
                        continue

            elif checkpoint_type == "input":
                # Try selector hints with input value
                if checkpoint.input_value:
                    value = self._apply_substitutions(
                        checkpoint.input_value,
                        ctx.config.substitutions,
                    )
                    for selector in checkpoint.selector_hints:
                        try:
                            await ctx.page.fill(selector, value, timeout=5000)
                            return True
                        except Exception:
                            continue

            elif checkpoint_type == "wait":
                # Just wait for the specified time
                delay = random.uniform(
                    checkpoint.timing.min_delay,
                    checkpoint.timing.max_delay,
                )
                await asyncio.sleep(delay)
                return True

            elif checkpoint_type == "scroll":
                # Scroll the page
                await ctx.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                return True

            # If we get here, fallback failed
            logger.warning("Fallback execution failed", checkpoint_id=checkpoint.id)
            return False

        except Exception as e:
            logger.error("Fallback execution error", error=str(e))
            return False

    async def _add_variation_delay(
        self,
        ctx: ExecutionContext,
        checkpoint: Checkpoint,
    ) -> None:
        """Add variation delay between checkpoints."""
        # Base delay from checkpoint timing
        base_min = checkpoint.timing.min_delay
        base_max = checkpoint.timing.max_delay

        # Modify based on variation level
        variation = ctx.config.variation_level
        if variation == VariationLevel.LOW:
            delay = random.uniform(base_min * 0.5, base_max * 0.8)
        elif variation == VariationLevel.MEDIUM:
            delay = random.uniform(base_min, base_max * 1.2)
        else:  # HIGH
            delay = random.uniform(base_min * 1.5, base_max * 2.0)

        # Add coherence engine variation if available
        if ctx.coherence_engine:
            try:
                profile = ctx.coherence_engine.get_current_profile()
                delay *= profile.speed_factor
            except Exception:
                pass

        await asyncio.sleep(delay)

    async def _cleanup(self, ctx: ExecutionContext) -> None:
        """Cleanup resources."""
        try:
            if ctx.browser:
                await ctx.browser.close()
        except Exception as e:
            logger.warning("Error closing browser", error=str(e))

    def get_execution_status(self, execution_id: str) -> FlowExecutionResult | None:
        """Get status of an active execution."""
        ctx = self._active_executions.get(execution_id)
        if ctx:
            return ctx.result
        return None

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution."""
        ctx = self._active_executions.get(execution_id)
        if not ctx:
            return False

        ctx.result.complete(False, "Cancelled by user")
        await self._cleanup(ctx)

        logger.info("Execution cancelled", execution_id=execution_id)
        return True


# Global executor instance
_executor: FlowExecutor | None = None


def get_flow_executor() -> FlowExecutor:
    """Get the global flow executor instance."""
    global _executor
    if _executor is None:
        _executor = FlowExecutor()
    return _executor
