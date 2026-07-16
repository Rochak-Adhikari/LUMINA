"""
Phase B.1 Verification Tests

Tests:
1. Environment check (must be in lumina conda env)
2. Memory write via MemoryStore API
3. Memory persistence across restarts
4. Tool permissions defaults

Run with: conda activate lumina && python backend/test_phase_b1.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# Change to project root
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root / "backend"))

print("=" * 60)
print("PHASE B.1 VERIFICATION TESTS")
print("=" * 60)

# Test 1: Environment Check
print("\n[TEST 1] Environment Check")
current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
if current_env != "lumina":
    print(f"❌ FAILED: Wrong conda environment")
    print(f"   Expected: lumina")
    print(f"   Current:  {current_env or '(none)'}")
    sys.exit(1)
else:
    print(f"✅ PASSED: Running in conda env '{current_env}'")

# Test 2: Import MemoryStore
print("\n[TEST 2] Import MemoryStore")
try:
    from memory_store import MemoryStore
    print("✅ PASSED: MemoryStore imported successfully")
except Exception as e:
    print(f"❌ FAILED: Could not import MemoryStore: {e}")
    sys.exit(1)

# Test 3: Create test memory database
print("\n[TEST 3] Create Test Memory Database")
test_db = "backend/test_memory_verify.db"
if os.path.exists(test_db):
    os.remove(test_db)
    print(f"   Removed existing {test_db}")

try:
    store = MemoryStore(test_db)
    print(f"✅ PASSED: Created database at {test_db}")
except Exception as e:
    print(f"❌ FAILED: Could not create database: {e}")
    sys.exit(1)

# Test 4: Write memories
print("\n[TEST 4] Write Test Memories")
try:
    id1 = store.add_memory("fact", "User is from Nepal")
    id2 = store.add_memory("preference", "User prefers casual Nepali with English mixing")
    id3 = store.add_memory("fact", "User is building an AI companion")
    print(f"✅ PASSED: Wrote 3 memories (IDs: {id1}, {id2}, {id3})")
except Exception as e:
    print(f"❌ FAILED: Could not write memories: {e}")
    sys.exit(1)

# Test 5: Read memories back
print("\n[TEST 5] Read Memories")
try:
    memories = store.get_memories(limit=10, update_access=False)
    if len(memories) != 3:
        print(f"❌ FAILED: Expected 3 memories, got {len(memories)}")
        sys.exit(1)
    
    print(f"✅ PASSED: Retrieved {len(memories)} memories:")
    for m in memories:
        print(f"   [{m['type']}] {m['content']}")
except Exception as e:
    print(f"❌ FAILED: Could not read memories: {e}")
    sys.exit(1)

# Test 6: Memory persistence (simulate restart)
print("\n[TEST 6] Memory Persistence")
try:
    del store  # Close connection
    
    # Reconnect
    store2 = MemoryStore(test_db)
    memories2 = store2.get_memories(limit=10, update_access=False)
    
    if len(memories2) != 3:
        print(f"❌ FAILED: Expected 3 memories after reconnect, got {len(memories2)}")
        sys.exit(1)
    
    print(f"✅ PASSED: Memories persisted across reconnection")
except Exception as e:
    print(f"❌ FAILED: Persistence check failed: {e}")
    sys.exit(1)

# Test 7: Memory context retrieval
print("\n[TEST 7] Memory Context Retrieval")
try:
    context = store2.get_memory_context(max_facts=5, max_preferences=3)
    
    if not context:
        print(f"❌ FAILED: Empty context returned")
        sys.exit(1)
    
    if "User is from Nepal" not in context:
        print(f"❌ FAILED: Expected fact not in context")
        sys.exit(1)
    
    print(f"✅ PASSED: Context generated ({len(context)} chars)")
    print("\nContext Preview:")
    print("-" * 60)
    print(context[:200] + "...")
except Exception as e:
    print(f"❌ FAILED: Context retrieval failed: {e}")
    sys.exit(1)

# Test 8: Tool permissions defaults
print("\n[TEST 8] Tool Permissions Defaults")
try:
    import json
    
    # Load server.py to check DEFAULT_SETTINGS
    server_path = project_root / "backend" / "server.py"
    with open(server_path, 'r', encoding='utf-8') as f:
        server_code = f.read()
    
    # Check if all tool permissions are False
    expected_disabled = [
        '"generate_cad": False',
        '"run_web_agent": False',
        '"write_file": False',
        '"read_directory": False',
        '"read_file": False',
        '"create_project": False',
        '"switch_project": False',
        '"list_projects": False',
        '"discover_printers": False',
        '"print_stl": False',
    ]
    
    all_disabled = all(perm in server_code for perm in expected_disabled)
    
    if all_disabled:
        print(f"✅ PASSED: All tools disabled by default")
    else:
        print(f"❌ FAILED: Some tools still enabled by default")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FAILED: Could not verify tool permissions: {e}")
    sys.exit(1)

# Test 9: Verify main memory database initialization
print("\n[TEST 9] Main Memory Database")
main_db = "backend/lumina_memory.db"
try:
    main_store = MemoryStore(main_db)
    stats = main_store.get_stats()
    print(f"✅ PASSED: Main database exists")
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   By type: {stats.get('by_type', {})}")
except Exception as e:
    print(f"❌ FAILED: Could not access main database: {e}")
    sys.exit(1)

# Cleanup
print("\n[CLEANUP]")
if os.path.exists(test_db):
    os.remove(test_db)
    print(f"   Removed {test_db}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✅")
print("=" * 60)
print("\nPhase B.1 verification complete:")
print("  ✓ Environment enforcement working")
print("  ✓ Memory store operational")
print("  ✓ Memory persistence confirmed")
print("  ✓ All tools disabled by default")
print("\nNext steps:")
print("  1. Start server: cd backend && python server.py")
print("  2. Test /remember command in chat UI")
print("  3. Test /memory command to list entries")
print("=" * 60)
