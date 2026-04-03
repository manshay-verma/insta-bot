import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
root = Path(__file__).parent
sys.path.insert(0, str(root))

from orchestrator import UnifiedWorker, AdapterType, TaskType

async def test():
    print("Initializing UnifiedWorker...")
    worker = UnifiedWorker(account_id=1)
    
    try:
        # We don't need to start_session for just initializing the adapter
        print("Getting Playwright adapter...")
        adapter = await worker.get_adapter(AdapterType.PLAYWRIGHT)
        print(f"Adapter initialized: {adapter.is_initialized}")
    except Exception as e:
        print(f"Died with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
