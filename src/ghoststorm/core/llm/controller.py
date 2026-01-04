"""LLM Controller - executes browser actions based on LLM decisions."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import structlog
from pydantic import BaseModel, Field

from ghoststorm.core.llm.messages import Conversation, SystemMessage, UserMessage
from ghoststorm.core.llm.prompts import (
    BROWSER_AGENT_SYSTEM_PROMPT,
    build_analysis_prompt,
    build_captcha_prompt,
    build_error_recovery_prompt,
)
from ghoststorm.core.llm.service import LLMService, ProviderType
from ghoststorm.core.llm.vision import (
    VisionAnalysis,
    VisionConfig,
    VisionMode,
    build_vision_prompt,
    capture_screenshot,
)

if TYPE_CHECKING:
    from ghoststorm.core.browser.protocol import IPage
    from ghoststorm.core.dom.service import DOMService

logger = structlog.get_logger(__name__)


class ActionType(str, Enum):
    """Types of browser actions."""

    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    NAVIGATE = "navigate"
    WAIT = "wait"
    EXTRACT = "extract"
    SCREENSHOT = "screenshot"


class BrowserAction(BaseModel):
    """A single browser action to execute."""

    type: ActionType
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    duration: float | None = None
    attribute: str | None = None
    reason: str = ""


class PageAnalysis(BaseModel):
    """Analysis of a page state."""

    analysis: str = Field(description="Description of current page state")
    is_complete: bool = Field(description="Whether the task is complete")
    next_action: BrowserAction | None = Field(default=None, description="Next action to take")
    confidence: float = Field(ge=0, le=1, description="Confidence in the analysis")
    extracted_data: dict[str, Any] | None = Field(default=None, description="Extracted data")


class TaskResult(BaseModel):
    """Result of executing a task."""

    success: bool
    steps_taken: int = 0
    extracted_data: dict[str, Any] | None = None
    error: str | None = None
    final_url: str | None = None


class ControllerMode(str, Enum):
    """Operating modes for the controller."""

    ASSIST = "assist"  # Suggest actions, human approves
    AUTONOMOUS = "autonomous"  # Execute actions automatically


@dataclass
class ControllerConfig:
    """Configuration for LLM controller."""

    mode: ControllerMode = ControllerMode.ASSIST
    max_steps: int = 20
    step_delay: float = 0.5  # Delay between steps (seconds)
    screenshot_on_error: bool = True
    min_confidence: float = 0.5  # Minimum confidence to execute action
    timeout_per_step: float = 30.0

    # Vision settings (hybrid mode like browser-use)
    vision_mode: VisionMode = VisionMode.AUTO  # off, auto, always
    vision_config: VisionConfig = field(default_factory=VisionConfig)
    vision_fallback_threshold: float = 0.6  # Use vision if DOM confidence below this


@dataclass
class StepResult:
    """Result of a single execution step."""

    step_number: int
    action: BrowserAction | None
    success: bool
    error: str | None = None
    screenshot: bytes | None = None


class LLMController:
    """
    Controls browser automation using LLM decisions.

    Supports two modes:
    - ASSIST: Analyzes pages and suggests actions (human approves)
    - AUTONOMOUS: Executes actions automatically until task completion
    """

    def __init__(
        self,
        llm_service: LLMService,
        dom_service: DOMService | None = None,
        config: ControllerConfig | None = None,
    ) -> None:
        """
        Initialize LLM controller.

        Args:
            llm_service: LLM service for completions
            dom_service: DOM service for page analysis (optional)
            config: Controller configuration
        """
        self.llm_service = llm_service
        self.dom_service = dom_service
        self.config = config or ControllerConfig()
        self._conversation = Conversation()
        self._step_history: list[StepResult] = []

    @property
    def mode(self) -> ControllerMode:
        """Get current controller mode."""
        return self.config.mode

    def set_mode(self, mode: ControllerMode) -> None:
        """Set controller mode."""
        self.config.mode = mode
        logger.info("Controller mode changed", mode=mode.value)

    def reset(self) -> None:
        """Reset controller state for new task."""
        self._conversation = Conversation()
        self._step_history = []

    async def analyze_page(
        self,
        page: IPage,
        task: str,
        provider: ProviderType | None = None,
        use_vision: bool | None = None,
    ) -> PageAnalysis:
        """
        Analyze current page and get suggested action.

        Supports hybrid DOM+Vision mode like browser-use:
        - VisionMode.OFF: DOM only
        - VisionMode.AUTO: Try DOM first, use vision if low confidence
        - VisionMode.ALWAYS: Always include screenshot

        Args:
            page: Browser page to analyze
            task: Task description
            provider: LLM provider to use
            use_vision: Override vision mode for this call

        Returns:
            Page analysis with suggested action
        """
        # Determine vision mode
        vision_mode = self.config.vision_mode
        if use_vision is True:
            vision_mode = VisionMode.ALWAYS
        elif use_vision is False:
            vision_mode = VisionMode.OFF

        # Get page state
        url = await page.url()
        dom_state = await self._get_dom_state(page)

        # Build prompt
        prompt = build_analysis_prompt(task, url, dom_state)

        # Initialize conversation if empty
        if not self._conversation.messages:
            self._conversation.add_system(BROWSER_AGENT_SYSTEM_PROMPT)

        # Add user message
        self._conversation.add_user(prompt)

        try:
            # Get provider instance to check vision support
            llm_provider = self.llm_service.get_provider(provider)

            # Determine if we should use vision
            should_use_vision = False
            screenshot = None

            if vision_mode == VisionMode.ALWAYS:
                should_use_vision = hasattr(llm_provider, "supports_vision") and llm_provider.supports_vision
            elif vision_mode == VisionMode.AUTO:
                # We'll check confidence after DOM analysis
                pass

            # Capture screenshot if needed
            if should_use_vision or vision_mode == VisionMode.AUTO:
                try:
                    screenshot = await capture_screenshot(page, self.config.vision_config)
                except Exception as e:
                    logger.warning("Failed to capture screenshot", error=str(e))

            # First try DOM-based analysis
            if should_use_vision and screenshot and hasattr(llm_provider, "complete_with_vision"):
                # Use vision directly
                response = await llm_provider.complete_with_vision(
                    messages=self._conversation.messages,
                    screenshot=screenshot,
                    temperature=0.2,
                )
            else:
                # DOM-based analysis
                response = await self.llm_service.complete(
                    messages=self._conversation.messages,
                    temperature=0.2,
                    provider=provider,
                )

            # Parse response
            analysis = self._parse_analysis(response.content)

            # AUTO mode: If confidence is low and we have screenshot, retry with vision
            if (
                vision_mode == VisionMode.AUTO
                and analysis.confidence < self.config.vision_fallback_threshold
                and screenshot
                and hasattr(llm_provider, "complete_with_vision")
                and llm_provider.supports_vision
            ):
                logger.info(
                    "Low confidence, retrying with vision",
                    dom_confidence=analysis.confidence,
                    threshold=self.config.vision_fallback_threshold,
                )

                # Retry with vision
                vision_response = await llm_provider.complete_with_vision(
                    messages=self._conversation.messages,
                    screenshot=screenshot,
                    temperature=0.2,
                )

                vision_analysis = self._parse_analysis(vision_response.content)

                # Use vision result if better
                if vision_analysis.confidence > analysis.confidence:
                    analysis = vision_analysis
                    response = vision_response

            # Add assistant response to conversation
            self._conversation.add_assistant(response.content)

            logger.debug(
                "Page analyzed",
                url=url,
                is_complete=analysis.is_complete,
                next_action=analysis.next_action.type if analysis.next_action else None,
                confidence=analysis.confidence,
                used_vision=should_use_vision or (vision_mode == VisionMode.AUTO and screenshot is not None),
            )

            return analysis

        except Exception as e:
            logger.error("Failed to analyze page", error=str(e))
            raise

    async def analyze_with_vision(
        self,
        page: IPage,
        task: str,
        provider: ProviderType | None = None,
    ) -> VisionAnalysis:
        """
        Analyze page using vision (screenshot) only.

        Args:
            page: Browser page
            task: Task description
            provider: LLM provider

        Returns:
            Vision analysis result
        """
        llm_provider = self.llm_service.get_provider(provider)

        if not hasattr(llm_provider, "supports_vision") or not llm_provider.supports_vision:
            raise ValueError(f"Provider does not support vision")

        # Capture screenshot
        screenshot = await capture_screenshot(page, self.config.vision_config)

        # Build vision prompt
        prompt = build_vision_prompt(task)

        # Analyze with vision
        analysis = await llm_provider.analyze_screenshot(screenshot, prompt)

        logger.debug(
            "Vision analysis complete",
            description_length=len(analysis.description),
            has_coordinates=analysis.coordinates is not None,
            confidence=analysis.confidence,
        )

        return analysis

    async def click_at_coordinates(
        self,
        page: IPage,
        x: int,
        y: int,
    ) -> bool:
        """
        Click at specific pixel coordinates (for vision-based actions).

        Args:
            page: Browser page
            x: X coordinate
            y: Y coordinate

        Returns:
            True if click succeeded
        """
        try:
            await page.mouse.click(x, y)
            logger.debug("Clicked at coordinates", x=x, y=y)
            return True
        except Exception as e:
            logger.error("Failed to click at coordinates", x=x, y=y, error=str(e))
            return False

    async def execute_task(
        self,
        page: IPage,
        task: str,
        provider: ProviderType | None = None,
    ) -> TaskResult:
        """
        Execute task autonomously.

        Args:
            page: Browser page
            task: Task to accomplish
            provider: LLM provider to use

        Returns:
            Task execution result

        Raises:
            ValueError: If not in autonomous mode
        """
        if self.config.mode != ControllerMode.AUTONOMOUS:
            raise ValueError("Controller not in autonomous mode. Use set_mode() first.")

        self.reset()
        logger.info("Starting autonomous task execution", task=task)

        for step in range(self.config.max_steps):
            try:
                # Analyze current state
                analysis = await self.analyze_page(page, task, provider)

                # Check if complete
                if analysis.is_complete:
                    final_url = await page.url()
                    logger.info(
                        "Task completed successfully",
                        steps=step + 1,
                        final_url=final_url,
                    )
                    return TaskResult(
                        success=True,
                        steps_taken=step + 1,
                        extracted_data=analysis.extracted_data,
                        final_url=final_url,
                    )

                # Check confidence threshold
                if analysis.confidence < self.config.min_confidence:
                    logger.warning(
                        "Low confidence, stopping",
                        confidence=analysis.confidence,
                        threshold=self.config.min_confidence,
                    )
                    return TaskResult(
                        success=False,
                        steps_taken=step + 1,
                        error=f"Low confidence ({analysis.confidence:.2f}) below threshold",
                    )

                # Execute action
                if analysis.next_action:
                    step_result = await self._execute_action(page, analysis.next_action, step + 1)
                    self._step_history.append(step_result)

                    if not step_result.success:
                        # Try error recovery
                        recovered = await self._attempt_recovery(
                            page, task, analysis.next_action, step_result.error or "", provider
                        )
                        if not recovered:
                            return TaskResult(
                                success=False,
                                steps_taken=step + 1,
                                error=step_result.error,
                            )

                # Delay between steps
                await asyncio.sleep(self.config.step_delay)

            except Exception as e:
                logger.error("Task execution error", step=step + 1, error=str(e))
                return TaskResult(
                    success=False,
                    steps_taken=step + 1,
                    error=str(e),
                )

        # Max steps reached
        final_url = await page.url()
        logger.warning("Max steps reached", max_steps=self.config.max_steps)
        return TaskResult(
            success=False,
            steps_taken=self.config.max_steps,
            error=f"Max steps ({self.config.max_steps}) exceeded",
            final_url=final_url,
        )

    async def execute_action(
        self,
        page: IPage,
        action: BrowserAction,
    ) -> StepResult:
        """
        Execute a single browser action.

        Args:
            page: Browser page
            action: Action to execute

        Returns:
            Step result
        """
        step_num = len(self._step_history) + 1
        result = await self._execute_action(page, action, step_num)
        self._step_history.append(result)
        return result

    async def detect_captcha(
        self,
        page: IPage,
        provider: ProviderType | None = None,
    ) -> dict[str, Any]:
        """
        Detect if page has CAPTCHA challenge.

        Args:
            page: Browser page
            provider: LLM provider

        Returns:
            CAPTCHA detection result
        """
        dom_state = await self._get_dom_state(page)
        prompt = build_captcha_prompt(dom_state)

        response = await self.llm_service.complete(
            messages=[
                SystemMessage(content="You are a CAPTCHA detection specialist."),
                UserMessage(content=prompt),
            ],
            temperature=0.1,
            provider=provider,
        )

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"has_captcha": False, "error": "Failed to parse response"}

    async def _get_dom_state(self, page: IPage) -> str:
        """Get DOM state as string for LLM."""
        if self.dom_service:
            try:
                dom_state = await self.dom_service.extract_dom(page)
                return dom_state.to_prompt()
            except Exception as e:
                logger.warning("Failed to extract DOM", error=str(e))

        # Fallback: basic page info
        try:
            title = await page.title()
            url = await page.url()
            return f"URL: {url}\nTitle: {title}\n(Full DOM extraction unavailable)"
        except Exception:
            return "(Page state unavailable)"

    async def _execute_action(
        self,
        page: IPage,
        action: BrowserAction,
        step_number: int,
    ) -> StepResult:
        """Execute a browser action."""
        logger.debug(
            "Executing action",
            step=step_number,
            type=action.type,
            selector=action.selector,
            reason=action.reason,
        )

        try:
            match action.type:
                case ActionType.CLICK:
                    if not action.selector:
                        raise ValueError("Click action requires selector")
                    await page.click(action.selector, timeout=self.config.timeout_per_step * 1000)

                case ActionType.TYPE:
                    if not action.selector or action.value is None:
                        raise ValueError("Type action requires selector and value")
                    await page.fill(action.selector, action.value, timeout=self.config.timeout_per_step * 1000)

                case ActionType.SCROLL:
                    scroll_amount = int(action.value) if action.value else 300
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

                case ActionType.NAVIGATE:
                    if not action.url:
                        raise ValueError("Navigate action requires url")
                    await page.goto(action.url, timeout=self.config.timeout_per_step * 1000)

                case ActionType.WAIT:
                    duration = action.duration or 1.0
                    await asyncio.sleep(duration)

                case ActionType.EXTRACT:
                    if not action.selector:
                        raise ValueError("Extract action requires selector")
                    # Extraction is handled in analysis response
                    pass

                case ActionType.SCREENSHOT:
                    # Screenshots are handled separately
                    pass

                case _:
                    raise ValueError(f"Unknown action type: {action.type}")

            return StepResult(
                step_number=step_number,
                action=action,
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error("Action failed", step=step_number, error=error_msg)

            screenshot = None
            if self.config.screenshot_on_error:
                try:
                    screenshot = await page.screenshot(type="png")
                except Exception:
                    pass

            return StepResult(
                step_number=step_number,
                action=action,
                success=False,
                error=error_msg,
                screenshot=screenshot,
            )

    async def _attempt_recovery(
        self,
        page: IPage,
        task: str,
        failed_action: BrowserAction,
        error: str,
        provider: ProviderType | None,
    ) -> bool:
        """Attempt to recover from a failed action."""
        logger.info("Attempting error recovery", error=error)

        url = await page.url()
        prompt = build_error_recovery_prompt(
            error=error,
            action=json.dumps(failed_action.model_dump()),
            url=url,
        )

        try:
            response = await self.llm_service.complete(
                messages=[
                    SystemMessage(content=BROWSER_AGENT_SYSTEM_PROMPT),
                    UserMessage(content=prompt),
                ],
                temperature=0.3,
                provider=provider,
            )

            recovery_analysis = self._parse_analysis(response.content)

            if recovery_analysis.next_action:
                result = await self._execute_action(
                    page, recovery_analysis.next_action, len(self._step_history) + 1
                )
                self._step_history.append(result)
                return result.success

        except Exception as e:
            logger.error("Recovery failed", error=str(e))

        return False

    def _parse_analysis(self, content: str) -> PageAnalysis:
        """Parse LLM response into PageAnalysis."""
        # Try to extract JSON from response
        content = content.strip()

        # Handle markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            data = json.loads(content)

            # Parse action if present
            next_action = None
            if data.get("next_action"):
                action_data = data["next_action"]
                next_action = BrowserAction(
                    type=ActionType(action_data.get("type", "click")),
                    selector=action_data.get("selector"),
                    value=action_data.get("value"),
                    url=action_data.get("url"),
                    duration=action_data.get("duration"),
                    attribute=action_data.get("attribute"),
                    reason=action_data.get("reason", ""),
                )

            return PageAnalysis(
                analysis=data.get("analysis", ""),
                is_complete=data.get("is_complete", False),
                next_action=next_action,
                confidence=data.get("confidence", 0.5),
                extracted_data=data.get("extracted_data"),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse LLM response", error=str(e), content=content[:200])
            # Return a safe default
            return PageAnalysis(
                analysis=f"Failed to parse response: {content[:200]}",
                is_complete=False,
                next_action=None,
                confidence=0.0,
            )

    def get_step_history(self) -> list[StepResult]:
        """Get history of executed steps."""
        return self._step_history.copy()

    def get_conversation_history(self) -> list[dict[str, str]]:
        """Get conversation history."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self._conversation.messages
        ]
