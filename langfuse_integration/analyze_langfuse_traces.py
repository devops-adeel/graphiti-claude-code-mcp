#!/usr/bin/env python3
"""
Analyze Langfuse traces to understand interrupt behavior in GTD Coach
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/Users/adeel/.env")

# Import Langfuse client
try:
    from langfuse import Langfuse
except ImportError:
    print("Error: langfuse package not installed")
    print("Install with: pip install langfuse")
    sys.exit(1)


def analyze_recent_traces(hours_back: int = 1, session_id: Optional[str] = None):
    """
    Analyze recent Langfuse traces to understand interrupt patterns

    Args:
        hours_back: How many hours back to look for traces
        session_id: Optional specific session ID to analyze
    """
    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        print(
            "Error: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY not found in environment"
        )
        return

    # Initialize client
    langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    print(f"Fetching traces from Langfuse...")
    print(f"Host: {host}")
    print(f"Looking back {hours_back} hours")
    print("-" * 80)

    # Get recent traces
    from_timestamp = datetime.now() - timedelta(hours=hours_back)

    # Fetch traces - using the API v3 interface
    traces = langfuse.api.trace.list(
        from_timestamp=from_timestamp, limit=10  # Get last 10 traces
    ).data

    if not traces:
        print("No traces found in the specified time range")
        return

    print(f"Found {len(traces)} traces")
    print("-" * 80)

    # Analyze each trace
    for i, trace in enumerate(traces, 1):
        print(f"\nTrace {i}: {trace.id}")
        print(f"  Name: {trace.name}")
        print(f"  Session ID: {trace.session_id}")
        print(f"  Timestamp: {trace.timestamp}")
        print(f"  User ID: {trace.user_id}")

        # Check if this trace matches our session filter
        if session_id and trace.session_id != session_id:
            print(f"  Skipping (not matching session {session_id})")
            continue

        # Get observations for this trace
        observations = langfuse.api.observations.get_many(trace_id=trace.id)

        print(f"  Observations: {len(observations)}")

        # Look for conversation tools and interrupts
        interrupt_found = False
        conversation_tools = []

        for obs in observations:
            # Check if this is a tool call
            if obs.name and "check_in_with_user" in obs.name:
                conversation_tools.append(obs.name)
                print(f"    - Conversation tool: {obs.name}")

                # Check input/output for interrupt patterns
                if obs.input:
                    print(f"      Input: {json.dumps(obs.input, indent=2)[:200]}")
                if obs.output:
                    print(f"      Output: {json.dumps(obs.output, indent=2)[:200]}")

                    # Look for interrupt indicators
                    output_str = str(obs.output)
                    if "__interrupt__" in output_str:
                        interrupt_found = True
                        print(f"      🔔 INTERRUPT FOUND in output!")

            elif obs.name and "wait_for_user" in obs.name:
                conversation_tools.append(obs.name)
                print(f"    - Conversation tool: {obs.name}")

            elif obs.name and "confirm_with_user" in obs.name:
                conversation_tools.append(obs.name)
                print(f"    - Conversation tool: {obs.name}")

        # Summary for this trace
        print(f"  Summary:")
        print(f"    - Conversation tools called: {len(conversation_tools)}")
        print(f"    - Interrupt detected: {'Yes' if interrupt_found else 'No'}")

        # Check for scores (might indicate completion or errors)
        scores = langfuse.api.score_v_2.get(trace_id=trace.id)
        if scores:
            print(f"    - Scores: {len(scores)}")
            for score in scores:
                print(f"      • {score.name}: {score.value}")

        print("-" * 80)

    # Flush any pending events
    langfuse.flush()
    print("\nAnalysis complete!")


def get_trace_details(trace_id: str):
    """
    Get detailed information about a specific trace

    Args:
        trace_id: The trace ID to analyze
    """
    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    print(f"Fetching trace {trace_id}...")

    # Get the trace
    trace = langfuse.api.trace.get(trace_id)

    if not trace:
        print(f"Trace {trace_id} not found")
        return

    print(f"Trace: {trace.name}")
    print(f"Session: {trace.session_id}")
    print(f"Timestamp: {trace.timestamp}")

    # Get all observations
    observations = langfuse.api.observations.get_many(trace_id=trace_id)

    print(f"\nObservations ({len(observations)}):")
    for obs in observations:
        print(f"  - {obs.name}")
        print(f"    Type: {obs.type}")
        print(f"    Start: {obs.start_time}")
        print(f"    End: {obs.end_time}")

        if obs.input:
            print(f"    Input: {json.dumps(obs.input, indent=4)[:500]}")
        if obs.output:
            print(f"    Output: {json.dumps(obs.output, indent=4)[:500]}")

        if obs.metadata:
            print(f"    Metadata: {json.dumps(obs.metadata, indent=4)[:500]}")

        print()

    langfuse.flush()


def analyze_phase_transition(trace_id: str, observations: List[Any]) -> Dict[str, Any]:
    """
    Analyze phase transitions within a trace to detect state loss and score changes

    Args:
        trace_id: The trace ID being analyzed
        observations: List of observations for the trace

    Returns:
        Dict containing transition analysis
    """
    transitions = []
    current_phase = None
    current_state = {}

    for i, obs in enumerate(observations):
        # Extract phase from observation metadata or input
        phase = None
        if obs.metadata and isinstance(obs.metadata, dict):
            phase = obs.metadata.get("phase") or obs.metadata.get("current_phase")
        elif obs.input and isinstance(obs.input, dict):
            phase = obs.input.get("phase") or obs.input.get("current_phase")

        # Detect phase transition
        if phase and phase != current_phase and current_phase is not None:
            transition = {
                "from_phase": current_phase,
                "to_phase": phase,
                "timestamp": obs.start_time,
                "observation_id": obs.id,
                "state_before": current_state.copy(),
            }

            # Extract new state after transition
            new_state = {}
            if obs.output and isinstance(obs.output, dict):
                new_state["tasks"] = obs.output.get("tasks", [])
                new_state["projects"] = obs.output.get("projects", [])
                new_state["priorities"] = obs.output.get("priorities", [])

            transition["state_after"] = new_state

            # Check for state loss
            state_lost = []
            for key in ["tasks", "projects", "priorities"]:
                if (
                    key in current_state
                    and current_state[key]
                    and key in new_state
                    and not new_state[key]
                ):
                    state_lost.append(key)

            transition["state_lost"] = state_lost
            transitions.append(transition)

            current_state = new_state

        current_phase = phase

        # Update current state from observations
        if obs.output and isinstance(obs.output, dict):
            if "tasks" in obs.output:
                current_state["tasks"] = obs.output["tasks"]
            if "projects" in obs.output:
                current_state["projects"] = obs.output["projects"]
            if "priorities" in obs.output:
                current_state["priorities"] = obs.output["priorities"]

    return transitions


def extract_prompt_metadata(observations: List[Any]) -> Dict[str, Any]:
    """
    Extract prompt information from generation observations

    Args:
        observations: List of observations

    Returns:
        Dict containing prompt usage statistics
    """
    prompt_usage = {}

    for obs in observations:
        if obs.type == "GENERATION" or (obs.name and "generation" in obs.name.lower()):
            # Extract prompt info from metadata
            prompt_name = None
            prompt_version = None
            prompt_variables = {}

            if obs.metadata and isinstance(obs.metadata, dict):
                prompt_name = obs.metadata.get("prompt_name") or obs.metadata.get(
                    "prompt"
                )
                prompt_version = obs.metadata.get("prompt_version") or obs.metadata.get(
                    "version"
                )
                prompt_variables = obs.metadata.get("variables", {})

            # Also check input for prompt info
            if obs.input and isinstance(obs.input, dict):
                if not prompt_name:
                    prompt_name = obs.input.get("prompt_name")
                if "messages" in obs.input:
                    # Extract from messages if structured
                    messages = obs.input["messages"]
                    if messages and isinstance(messages, list) and len(messages) > 0:
                        # Look for system message that might contain prompt
                        for msg in messages:
                            if isinstance(msg, dict) and msg.get("role") == "system":
                                # Try to identify prompt from content patterns
                                content = msg.get("content", "")
                                if (
                                    "gtd" in content.lower()
                                    or "coach" in content.lower()
                                ):
                                    if "firm" in content.lower():
                                        prompt_name = prompt_name or "gtd-coach-firm"
                                    elif "gentle" in content.lower():
                                        prompt_name = prompt_name or "gtd-coach-gentle"
                                    elif "simple" in content.lower():
                                        prompt_name = prompt_name or "gtd-coach-simple"

            if prompt_name:
                if prompt_name not in prompt_usage:
                    prompt_usage[prompt_name] = {
                        "count": 0,
                        "versions": set(),
                        "variables_used": [],
                        "observation_ids": [],
                    }

                prompt_usage[prompt_name]["count"] += 1
                if prompt_version:
                    prompt_usage[prompt_name]["versions"].add(prompt_version)
                if prompt_variables:
                    prompt_usage[prompt_name]["variables_used"].append(prompt_variables)
                prompt_usage[prompt_name]["observation_ids"].append(obs.id)

    # Convert sets to lists for JSON serialization
    for prompt in prompt_usage.values():
        prompt["versions"] = list(prompt["versions"])

    return prompt_usage


def format_conversation_flow(
    observations: List[Any], show_metadata: bool = True
) -> str:
    """
    Format observations into a human-readable conversation flow

    Args:
        observations: List of observations
        show_metadata: Whether to show inline metadata

    Returns:
        Formatted conversation string
    """
    output = []

    for obs in observations:
        timestamp = (
            obs.start_time.strftime("%H:%M:%S") if obs.start_time else "??:??:??"
        )

        # Determine the type of interaction
        if obs.name and "check_in" in obs.name.lower():
            output.append(f"\n[{timestamp}] 🔔 INTERRUPT - Agent checking in with user")
        elif obs.name and "wait_for" in obs.name.lower():
            output.append(f"\n[{timestamp}] ⏸️ WAITING for user input")
        elif obs.type == "GENERATION":
            output.append(f"\n[{timestamp}] 🤖 GENERATION")

        # Show input/output in conversational format
        if obs.input:
            if isinstance(obs.input, dict):
                if "messages" in obs.input:
                    messages = obs.input["messages"]
                    if isinstance(messages, list):
                        for msg in messages[-2:]:  # Show last 2 messages for context
                            if isinstance(msg, dict):
                                role = msg.get("role", "unknown")
                                content = msg.get("content", "")[:200]
                                if role == "user":
                                    output.append(f"  👤 User: {content}")
                                elif role == "assistant":
                                    output.append(f"  🤖 Agent: {content}")
                elif "query" in obs.input:
                    output.append(f"  📝 Query: {obs.input['query'][:200]}")

        if obs.output:
            if isinstance(obs.output, str):
                output.append(f"  → Response: {obs.output[:200]}")
            elif isinstance(obs.output, dict):
                if "__interrupt__" in obs.output:
                    output.append(f"  ⚠️ INTERRUPT TRIGGERED")
                elif "content" in obs.output:
                    output.append(f"  → Response: {obs.output['content'][:200]}")

        # Show metadata if requested
        if show_metadata and obs.metadata:
            if isinstance(obs.metadata, dict):
                phase = obs.metadata.get("phase", obs.metadata.get("current_phase"))
                if phase:
                    output.append(f"  📍 Phase: {phase}")
                time_remaining = obs.metadata.get("time_remaining")
                if time_remaining:
                    output.append(f"  ⏱️ Time remaining: {time_remaining} min")

    return "\n".join(output)


def validate_state_continuity(observations: List[Any]) -> Dict[str, Any]:
    """
    Validate that state is maintained properly across observations

    Args:
        observations: List of observations

    Returns:
        Dict containing validation results
    """
    validation_results = {"state_losses": [], "inconsistencies": [], "warnings": []}

    tracked_state = {"tasks": [], "projects": [], "priorities": []}

    for i, obs in enumerate(observations):
        # Extract state from observation
        current_state = {}

        if obs.output and isinstance(obs.output, dict):
            for key in ["tasks", "projects", "priorities"]:
                if key in obs.output:
                    current_state[key] = obs.output[key]

        # Check for state loss
        for key in tracked_state:
            if tracked_state[key] and key in current_state and not current_state[key]:
                validation_results["state_losses"].append(
                    {
                        "observation_id": obs.id,
                        "timestamp": obs.start_time,
                        "lost_item": key,
                        "previous_value": tracked_state[key],
                        "observation_name": obs.name,
                    }
                )

        # Update tracked state
        for key in current_state:
            tracked_state[key] = current_state[key]

        # Check for memory relevance issues
        if obs.name and "memory" in obs.name.lower():
            if obs.metadata and isinstance(obs.metadata, dict):
                relevance = obs.metadata.get("relevance_score", 1.0)
                if relevance < 0.5:
                    validation_results["warnings"].append(
                        {
                            "type": "low_memory_relevance",
                            "observation_id": obs.id,
                            "relevance_score": relevance,
                            "timestamp": obs.start_time,
                        }
                    )

    return validation_results


def analyze_test_failure(session_id: str, return_data: bool = False):
    """
    Analyze Langfuse traces for a failed test session - AI-optimized output

    Args:
        session_id: The test session ID to analyze
        return_data: If True, return data instead of printing (for fixture use)

    Returns:
        Dict with analysis data if return_data=True, None otherwise
    """
    # Load real API keys from ~/.env if available
    home_env = os.path.expanduser("~/.env")
    if os.path.exists(home_env):
        load_dotenv(home_env)

    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        msg = (
            "ERROR: Langfuse API keys not found. Check ~/.env or environment variables."
        )
        if return_data:
            return {"error": msg}
        print(msg)
        return

    langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    analysis = {
        "session_id": session_id,
        "traces": [],
        "errors": [],
        "tool_calls": [],
        "interrupts": [],
        "state_transitions": [],
    }

    # Fetch traces for this session
    traces = langfuse.api.trace.list(
        session_id=session_id,
        limit=50,  # Get up to 50 traces for comprehensive analysis
    ).data

    if not traces:
        msg = f"No traces found for session {session_id}"
        if return_data:
            analysis["error"] = msg
            return analysis
        print(msg)
        return

    # Analyze each trace
    for trace in traces:
        trace_data = {
            "id": trace.id,
            "name": trace.name,
            "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
            "observations": [],
        }

        # Get observations for detailed analysis
        observations = langfuse.api.observations.get_many(trace_id=trace.id)

        for obs in observations:
            obs_data = {
                "name": obs.name,
                "type": obs.type,
                "start": obs.start_time.isoformat() if obs.start_time else None,
                "end": obs.end_time.isoformat() if obs.end_time else None,
            }

            # Extract key information for AI analysis
            if obs.input:
                obs_data["input"] = obs.input

            if obs.output:
                obs_data["output"] = obs.output

                # Detect errors
                output_str = str(obs.output)
                if "error" in output_str.lower() or "exception" in output_str.lower():
                    analysis["errors"].append(
                        {
                            "trace": trace.name,
                            "observation": obs.name,
                            "details": obs.output,
                        }
                    )

                # Detect interrupts
                if "__interrupt__" in output_str:
                    analysis["interrupts"].append(
                        {
                            "trace": trace.name,
                            "observation": obs.name,
                            "interrupt_data": obs.output,
                        }
                    )

            # Track tool calls
            if obs.name and (
                "tool" in obs.name.lower()
                or "check_in" in obs.name
                or "wait_for" in obs.name
            ):
                analysis["tool_calls"].append(
                    {
                        "trace": trace.name,
                        "tool": obs.name,
                        "input": obs.input if obs.input else {},
                        "output": obs.output if obs.output else {},
                    }
                )

            # Track state transitions
            if obs.metadata and "state" in str(obs.metadata):
                analysis["state_transitions"].append(
                    {
                        "trace": trace.name,
                        "observation": obs.name,
                        "metadata": obs.metadata,
                    }
                )

            trace_data["observations"].append(obs_data)

        analysis["traces"].append(trace_data)

    langfuse.flush()

    if return_data:
        return analysis

    # Print AI-optimized analysis
    print("\n" + "=" * 80)
    print(f"TEST FAILURE ANALYSIS FOR SESSION: {session_id}")
    print("=" * 80)

    print(f"\n📊 TRACE SUMMARY:")
    print(f"  Total traces: {len(analysis['traces'])}")
    print(f"  Errors found: {len(analysis['errors'])}")
    print(f"  Tool calls: {len(analysis['tool_calls'])}")
    print(f"  Interrupts: {len(analysis['interrupts'])}")
    print(f"  State transitions: {len(analysis['state_transitions'])}")

    if analysis["errors"]:
        print(f"\n❌ ERRORS DETECTED:")
        for error in analysis["errors"]:
            print(f"  - {error['trace']} → {error['observation']}")
            print(f"    {json.dumps(error['details'], indent=4)[:500]}")

    if analysis["interrupts"]:
        print(f"\n🔔 INTERRUPT PATTERNS:")
        for interrupt in analysis["interrupts"]:
            print(f"  - {interrupt['trace']} → {interrupt['observation']}")
            print(f"    {json.dumps(interrupt['interrupt_data'], indent=4)[:500]}")

    if analysis["tool_calls"]:
        print(f"\n🔧 TOOL CALL SEQUENCE:")
        for tool in analysis["tool_calls"][:10]:  # Show first 10
            print(f"  - {tool['tool']}")
            if tool["input"]:
                print(f"    Input: {json.dumps(tool['input'], indent=4)[:200]}")
            if tool["output"]:
                print(f"    Output: {json.dumps(tool['output'], indent=4)[:200]}")

    # Detailed trace flow for AI debugging
    print(f"\n📝 DETAILED TRACE FLOW:")
    for trace in analysis["traces"][:5]:  # Show first 5 traces in detail
        print(f"\n  Trace: {trace['name']} (ID: {trace['id'][:8]}...)")
        print(f"  Time: {trace['timestamp']}")
        print(f"  Observations:")
        for obs in trace["observations"][:10]:  # Show first 10 observations
            print(f"    • {obs['name']} ({obs['type']})")
            if "input" in obs and obs["input"]:
                print(f"      Input: {json.dumps(obs['input'])[:150]}")
            if "output" in obs and obs["output"]:
                print(f"      Output: {json.dumps(obs['output'])[:150]}")

    print("\n" + "=" * 80)
    print("END OF ANALYSIS")
    print("=" * 80)


def debug_session(session_id: str, focus: str = "all"):
    """
    Comprehensive debug mode for a session - combines all analysis features

    Args:
        session_id: The session ID to debug
        focus: What to focus on ('transitions', 'prompts', 'conversation', 'state', 'all')
    """
    print("\n" + "=" * 80)
    print(f"🔍 DEBUGGING SESSION: {session_id}")
    print("=" * 80)

    # Initialize Langfuse client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        print("❌ Error: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY not found")
        return

    langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    # Fetch traces for this session
    traces = langfuse.api.trace.list(session_id=session_id, limit=50).data

    if not traces:
        print(f"❌ No traces found for session {session_id}")
        return

    print(f"📊 Found {len(traces)} traces in session\n")

    issues_found = []

    for trace in traces:
        print(f"\n--- Analyzing Trace: {trace.name} ({trace.id[:8]}...) ---")

        # Get observations for detailed analysis
        observations = langfuse.api.observations.get_many(trace_id=trace.id)

        if not observations:
            print("  ⚠️ No observations found for this trace")
            continue

        # Get scores for this trace
        scores = langfuse.api.score_v_2.get(trace_id=trace.id)
        score_dict = {}
        if scores:
            for score in scores:
                score_dict[score.name] = score.value

        # 1. PHASE TRANSITION ANALYSIS
        if focus in ["transitions", "all"]:
            print("\n📍 PHASE TRANSITIONS:")
            transitions = analyze_phase_transition(trace.id, observations)
            if transitions:
                for trans in transitions:
                    print(f"  {trans['from_phase']} → {trans['to_phase']}")
                    if trans["state_lost"]:
                        print(f"    ❌ STATE LOST: {', '.join(trans['state_lost'])}")
                        issues_found.append(
                            f"State loss during {trans['from_phase']} → {trans['to_phase']}"
                        )

                    # Check scores around transition
                    print(f"    Scores at transition:")
                    for score_name, score_value in score_dict.items():
                        if score_value < 0.5:
                            print(f"      ⚠️ {score_name}: {score_value:.2f}")
                        else:
                            print(f"      ✅ {score_name}: {score_value:.2f}")
            else:
                print("  No phase transitions detected")

        # 2. PROMPT ANALYSIS
        if focus in ["prompts", "all"]:
            print("\n🎯 PROMPT USAGE:")
            prompt_usage = extract_prompt_metadata(observations)
            if prompt_usage:
                for prompt_name, usage in prompt_usage.items():
                    print(f"  {prompt_name}:")
                    print(f"    Used {usage['count']} times")
                    if usage["versions"]:
                        print(f"    Versions: {', '.join(map(str, usage['versions']))}")

                    # Correlate with scores
                    if score_dict:
                        avg_score = (
                            sum(score_dict.values()) / len(score_dict)
                            if score_dict
                            else 0
                        )
                        if avg_score < 0.5:
                            print(
                                f"    ⚠️ Low average score with this prompt: {avg_score:.2f}"
                            )
                            issues_found.append(f"Low scores with prompt {prompt_name}")
            else:
                print("  No prompt metadata found")

        # 3. CONVERSATION FLOW
        if focus in ["conversation", "all"]:
            print("\n💬 CONVERSATION FLOW:")
            conversation = format_conversation_flow(observations, show_metadata=True)
            if len(conversation) > 1000:
                # Show abbreviated version for long conversations
                lines = conversation.split("\n")
                print("\n".join(lines[:10]))
                print(f"  ... ({len(lines) - 20} lines omitted) ...")
                print("\n".join(lines[-10:]))
            else:
                print(conversation)

        # 4. STATE VALIDATION
        if focus in ["state", "all"]:
            print("\n✔️ STATE VALIDATION:")
            validation = validate_state_continuity(observations)
            if validation["state_losses"]:
                print("  ❌ STATE LOSSES DETECTED:")
                for loss in validation["state_losses"]:
                    print(f"    - Lost {loss['lost_item']} at {loss['timestamp']}")
                    print(
                        f"      Previous value: {loss['previous_value'][:100] if isinstance(loss['previous_value'], str) else loss['previous_value']}"
                    )
                    issues_found.append(f"State loss: {loss['lost_item']}")
            else:
                print("  ✅ No state losses detected")

            if validation["warnings"]:
                print("  ⚠️ WARNINGS:")
                for warning in validation["warnings"]:
                    if warning["type"] == "low_memory_relevance":
                        print(
                            f"    - Low memory relevance: {warning['relevance_score']:.2f}"
                        )
                        issues_found.append("Low memory relevance")

    # SUMMARY AND RECOMMENDATIONS
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)

    if issues_found:
        print("\n⚠️ ISSUES FOUND:")
        unique_issues = list(set(issues_found))
        for i, issue in enumerate(unique_issues, 1):
            print(f"  {i}. {issue}")

        print("\n💡 SUGGESTED FIXES:")
        for issue in unique_issues:
            if "State loss" in issue:
                print(
                    f"  • {issue}: Check prompt templates for missing state variables"
                )
                print(
                    f"    - Ensure {{tasks}}, {{projects}}, {{priorities}} are passed to prompts"
                )
                print(f"    - Verify checkpoint/persistence in LangGraph configuration")
            elif "Low scores" in issue:
                print(f"  • {issue}: Consider adjusting prompt parameters")
                print(f"    - Review temperature settings")
                print(f"    - Check if prompt version is appropriate for the phase")
            elif "Low memory relevance" in issue:
                print(f"  • {issue}: Review memory retrieval queries")
                print(f"    - Ensure phase-specific memory filtering")
                print(f"    - Check embedding quality and similarity thresholds")
    else:
        print("\n✅ No critical issues detected in this session")

    langfuse.flush()
    print("\n" + "=" * 80)
    print("Debug analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze Langfuse traces for GTD Coach"
    )
    parser.add_argument(
        "--hours", type=int, default=1, help="Hours to look back (default: 1)"
    )
    parser.add_argument("--session", type=str, help="Specific session ID to analyze")
    parser.add_argument("--trace", type=str, help="Specific trace ID to get details")
    parser.add_argument(
        "--test-failure",
        type=str,
        help="Analyze a test failure session with AI-optimized output",
    )

    # New debugging options
    parser.add_argument("--debug", type=str, help="Debug a session comprehensively")
    parser.add_argument(
        "--show-transitions", action="store_true", help="Focus on phase transitions"
    )
    parser.add_argument(
        "--prompt-analysis",
        action="store_true",
        help="Analyze prompt usage and performance",
    )
    parser.add_argument(
        "--show-conversation", action="store_true", help="Display conversation flow"
    )
    parser.add_argument(
        "--validate-state",
        action="store_true",
        help="Check for state continuity issues",
    )

    args = parser.parse_args()

    # Handle new debug modes
    if args.debug:
        # Determine focus based on other flags
        focus = "all"
        if args.show_transitions:
            focus = "transitions"
        elif args.prompt_analysis:
            focus = "prompts"
        elif args.show_conversation:
            focus = "conversation"
        elif args.validate_state:
            focus = "state"

        debug_session(args.debug, focus)
    elif args.test_failure:
        analyze_test_failure(args.test_failure)
    elif args.trace:
        get_trace_details(args.trace)
    elif args.session:
        # If specific analysis flags are set with session
        if (
            args.show_transitions
            or args.prompt_analysis
            or args.show_conversation
            or args.validate_state
        ):
            focus = []
            if args.show_transitions:
                focus.append("transitions")
            if args.prompt_analysis:
                focus.append("prompts")
            if args.show_conversation:
                focus.append("conversation")
            if args.validate_state:
                focus.append("state")

            # Use debug_session with specific focus
            debug_session(args.session, focus=",".join(focus) if focus else "all")
        else:
            # Default session analysis
            analyze_recent_traces(hours_back=args.hours, session_id=args.session)
    else:
        analyze_recent_traces(hours_back=args.hours, session_id=args.session)
