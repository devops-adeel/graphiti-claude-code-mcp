#!/usr/bin/env python3
"""
Test script to verify Langfuse SDK v3 connectivity
"""
import os
from langfuse import Langfuse
import httpx

print("=" * 60)
print("LANGFUSE SDK v3 TEST - INTERNAL NETWORK")
print("=" * 60)

host = os.environ.get("LANGFUSE_HOST")
public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

print(f"Host: {host}")
print(f"Public key: {public_key[:20]}..." if public_key else "No public key")
print(f"Secret key: {secret_key[:20]}..." if secret_key else "No secret key")

print("\nCreating Langfuse client...")
client = Langfuse(
    public_key=public_key,
    secret_key=secret_key,
    host=host,
    httpx_client=httpx.Client(timeout=10.0),
)

print("Testing SDK v3 methods...\n")
try:
    # Test api.trace.list()
    print("1. Testing api.trace.list()...")
    result = client.api.trace.list(limit=1)
    print(f"   ✅ SUCCESS - Returns: {type(result).__name__}")
    print(f"   ✅ Has .data attribute: {hasattr(result, 'data')}")

    if hasattr(result, "data"):
        if result.data:
            print(f"   ✅ Found {len(result.data)} trace(s)")
            trace = result.data[0]
            print(f"   ✅ First trace ID: {trace.id[:8]}...")
            print(f"   ✅ Trace name: {trace.name}")

            # Test api.trace.get()
            print("\n2. Testing api.trace.get()...")
            single = client.api.trace.get(trace.id)
            print(f"   ✅ SUCCESS - Retrieved trace: {single.id[:8]}...")

            # Test api.observations.get_many()
            print("\n3. Testing api.observations.get_many()...")
            obs = client.api.observations.get_many(trace_id=trace.id, limit=5)
            print(f"   ✅ SUCCESS - Returns: {type(obs).__name__}")
            if hasattr(obs, "data"):
                print(f"   ✅ Found {len(obs.data) if obs.data else 0} observation(s)")
        else:
            print("   ℹ️  No traces found (database is empty)")
            print("   ✅ But connection successful!")

    # Test api.score_v_2.get()
    print("\n4. Testing api.score_v_2.get()...")
    scores = client.api.score_v_2.get(limit=1)
    print(f"   ✅ SUCCESS - Returns: {type(scores).__name__}")
    if hasattr(scores, "data"):
        print(f"   ✅ Found {len(scores.data) if scores.data else 0} score(s)")

    print("\n" + "=" * 60)
    print("✅ ALL LANGFUSE SDK v3 METHODS WORKING!")
    print("✅ Connection to Langfuse server SUCCESSFUL!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback

    print("\nFull traceback:")
    traceback.print_exc()
