#!/usr/bin/env python3
"""
Track video documentation engagement using Graphiti's own memory system.

This script demonstrates how Graphiti can be used to learn from user interactions
with documentation, creating a feedback loop for continuous improvement.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graphiti_memory import get_shared_memory
from capture import get_capture_client


class VideoEngagementTracker:
    """Track and learn from video documentation engagement."""

    def __init__(self):
        self.memory = None
        self.capture = None

    async def initialize(self):
        """Initialize memory and capture clients."""
        self.memory = await get_shared_memory()
        self.capture = await get_capture_client()

    async def track_video_click(
        self,
        section: str,
        timestamp: Optional[str] = None,
        source: str = "README",
        user_persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track when a user clicks on the video or a specific section.

        Args:
            section: Which section was clicked (e.g., "full_video", "teaser", "one_mind")
            timestamp: Video timestamp if jumping to specific time
            source: Where the click originated (README, transcript, etc.)
            user_persona: If known (developer, researcher, decision_maker)
        """
        engagement_data = {
            "type": "video_click",
            "section": section,
            "timestamp": timestamp,
            "source": source,
            "persona": user_persona,
            "datetime": datetime.now(timezone.utc).isoformat(),
        }

        # Capture this as a pattern to learn from
        await self.capture.capture_solution(
            error=f"User seeking understanding via video documentation",
            solution=f"Directed to {section}"
            + (f" at {timestamp}" if timestamp else ""),
            context={
                "engagement": engagement_data,
                "documentation_type": "conceptual_video",
            },
        )

        return {
            "tracked": True,
            "engagement_id": f"video_{section}_{datetime.now(timezone.utc).timestamp()}",
        }

    async def track_watch_duration(
        self,
        duration_seconds: int,
        completed: bool = False,
        exit_point: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track how long someone watched the video.

        Args:
            duration_seconds: How long they watched
            completed: Did they watch to the end?
            exit_point: Timestamp where they stopped (if not completed)
        """
        # Calculate engagement quality
        total_duration = 338  # 5:38 in seconds
        engagement_rate = (duration_seconds / total_duration) * 100

        engagement_quality = (
            "high"
            if engagement_rate > 80
            else "medium" if engagement_rate > 50 else "low"
        )

        watch_data = {
            "duration_seconds": duration_seconds,
            "engagement_rate": f"{engagement_rate:.1f}%",
            "quality": engagement_quality,
            "completed": completed,
            "exit_point": exit_point,
        }

        # Learn from watch patterns
        await self.capture.capture_solution(
            error="Understanding user engagement with video content",
            solution=f"User watched {duration_seconds}s ({engagement_rate:.1f}%) - {engagement_quality} engagement",
            context={
                "watch_data": watch_data,
                "insights": self._generate_insights(engagement_rate, exit_point),
            },
        )

        return watch_data

    async def track_navigation_path(self, path: list[str]) -> Dict[str, Any]:
        """
        Track the user's navigation path to understand journey.

        Args:
            path: List of pages/sections visited (e.g., ["README", "video", "quickstart"])
        """
        # Analyze common patterns
        known_patterns = {
            ("README", "video", "quickstart"): "standard_onboarding",
            ("README", "video", "transcript"): "accessibility_focused",
            ("video", "philosophy", "quickstart"): "deep_understanding",
            ("README", "quickstart"): "video_skipped",
        }

        path_tuple = tuple(path[:3])  # Look at first 3 steps
        pattern = known_patterns.get(path_tuple, "custom_path")

        navigation_data = {
            "path": path,
            "pattern": pattern,
            "steps": len(path),
            "video_engaged": "video" in path,
        }

        # Capture navigation pattern
        await self.capture.capture_solution(
            error="Understanding user documentation journey",
            solution=f"User followed {pattern} pattern through {len(path)} steps",
            context=navigation_data,
        )

        return navigation_data

    async def analyze_engagement_patterns(self) -> Dict[str, Any]:
        """
        Analyze all video engagement patterns to find insights.
        """
        # Search for all video engagement memories
        results = await self.memory.search_with_temporal_weight(
            "video documentation engagement", filter_source="claude_code"
        )

        patterns = {
            "total_engagements": len(results),
            "common_sections": {},
            "average_engagement": 0,
            "personas": {},
            "navigation_patterns": {},
        }

        for result in results:
            # Extract and analyze patterns from memories
            if "engagement" in str(result):
                # Parse engagement data (simplified for example)
                patterns["total_engagements"] += 1

        # Generate actionable insights
        insights = self._generate_actionable_insights(patterns)

        # Store the analysis as a memory
        await self.capture.capture_solution(
            error="Analyzing video documentation effectiveness",
            solution=f"Generated insights from {patterns['total_engagements']} engagements",
            context={
                "patterns": patterns,
                "insights": insights,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {"patterns": patterns, "insights": insights}

    def _generate_insights(
        self, engagement_rate: float, exit_point: Optional[str]
    ) -> list[str]:
        """Generate insights from individual engagement."""
        insights = []

        if engagement_rate > 80:
            insights.append("High engagement - content resonates well")
        elif engagement_rate < 30:
            insights.append("Low engagement - consider shorter format or better hook")

        if exit_point:
            if "2:00" in exit_point:
                insights.append("Common exit at 2 minutes - consider chapter markers")
            elif "4:00" in exit_point:
                insights.append("Exit near climax - possibly too abstract?")

        return insights

    def _generate_actionable_insights(self, patterns: Dict[str, Any]) -> list[str]:
        """Generate actionable insights from pattern analysis."""
        insights = []

        if patterns["total_engagements"] > 100:
            insights.append(
                "High video engagement - consider creating more video content"
            )

        # Add more sophisticated analysis here
        insights.append("Consider A/B testing different video thumbnails")
        insights.append(
            "Track correlation between video views and successful implementations"
        )

        return insights


async def main():
    """Example usage and testing."""
    tracker = VideoEngagementTracker()
    await tracker.initialize()

    print("📊 Video Engagement Tracker Initialized")

    # Example: Track a video click
    result = await tracker.track_video_click(
        section="one_mind", timestamp="4:03", source="README", user_persona="developer"
    )
    print(f"✅ Tracked click: {result}")

    # Example: Track watch duration
    watch_result = await tracker.track_watch_duration(
        duration_seconds=245, completed=False, exit_point="4:05"  # Watched 4:05 of 5:38
    )
    print(f"⏱️ Watch metrics: {watch_result}")

    # Example: Track navigation path
    nav_result = await tracker.track_navigation_path(
        path=["README", "video", "transcript", "quickstart"]
    )
    print(f"🗺️ Navigation pattern: {nav_result['pattern']}")

    # Analyze patterns
    analysis = await tracker.analyze_engagement_patterns()
    print(f"\n📈 Engagement Analysis:")
    print(f"   Total engagements: {analysis['patterns']['total_engagements']}")
    print(f"   Insights: {', '.join(analysis['insights'])}")


if __name__ == "__main__":
    asyncio.run(main())
