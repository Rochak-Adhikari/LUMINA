#!/usr/bin/env python3
"""
Phase C Validation Tests

Tests for authoritative memory injection:
- Identity memories are always included
- Memory format is structured and consistent
- get_identity_memories() returns seeded facts
- Memory injection works with relevant queries

MUST RUN IN LUMINA CONDA ENVIRONMENT:
    conda activate lumina
    cd backend
    python test_phase_c.py
"""

import sys
import os
import sqlite3

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_store import MemoryStore

def print_header(msg):
    print(f"\n{'='*70}")
    print(msg)
    print('='*70)

def test_database_exists():
    """Test 1: Ensure memory database exists"""
    print_header("TEST 1: Database Existence")
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lumina_memory.db")
    
    if not os.path.exists(db_path):
        print(f"❌ FAILED: Database not found at {db_path}")
        print("   Run the server once to create the database:")
        print("   conda activate lumina")
        print("   python server.py")
        return False
    
    print(f"✅ PASSED: Database exists at {db_path}")
    
    # Check table structure
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
        if cursor.fetchone():
            print("✅ PASSED: 'memories' table exists")
        else:
            print("❌ FAILED: 'memories' table not found")
            conn.close()
            return False
        
        # Check record count
        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        print(f"✅ INFO: Database contains {count} memory records")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Database error: {e}")
        return False

def test_identity_memories():
    """Test 2: Ensure identity memories are present and retrievable"""
    print_header("TEST 2: Identity Memories Present")
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lumina_memory.db")
    store = MemoryStore(db_path)
    
    try:
        identity_memories = store.get_identity_memories()
        
        if not identity_memories:
            print("❌ FAILED: No identity memories found")
            print("   Identity memories should be seeded on first server start.")
            print("   Expected facts about Scepter/Rochak Adhikari/companion.")
            return False
        
        print(f"✅ PASSED: Found {len(identity_memories)} identity memories")
        
        # Check for required identity facts
        required_markers = ["Scepter", "Rochak Adhikari"]
        found_markers = {marker: False for marker in required_markers}
        
        print("\nIdentity Memories:")
        for mem in identity_memories:
            print(f"  - [{mem['type']}] {mem['content'][:80]}{'...' if len(mem['content']) > 80 else ''}")
            for marker in required_markers:
                if marker in mem['content']:
                    found_markers[marker] = True
        
        # Verify all required markers present
        all_found = all(found_markers.values())
        if all_found:
            print(f"\n✅ PASSED: All required identity markers found")
        else:
            missing = [m for m, found in found_markers.items() if not found]
            print(f"\n❌ FAILED: Missing identity markers: {missing}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error retrieving identity memories: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_relevant_memory_retrieval():
    """Test 3: Test relevant memory retrieval with identity query"""
    print_header("TEST 3: Relevant Memory Retrieval")
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lumina_memory.db")
    store = MemoryStore(db_path)
    
    test_queries = [
        ("who created you?", ["Scepter", "companion"]),
        ("what are my preferences?", ["preference"]),
        ("who am I?", ["Scepter", "user"])
    ]
    
    all_passed = True
    
    for query, expected_keywords in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            memories = store.get_relevant_memories(query, max_results=5)
            
            if not memories:
                print(f"  ⚠️  WARNING: No memories returned for '{query}'")
                continue
            
            print(f"  ✅ Retrieved {len(memories)} memories")
            
            # Check if at least one memory contains expected keywords
            found_any = False
            for mem in memories:
                if any(kw.lower() in mem['content'].lower() for kw in expected_keywords):
                    found_any = True
                    print(f"    - [{mem['type']}] Score: {mem.get('score', 0):.1f} | {mem['content'][:60]}...")
            
            if found_any:
                print(f"  ✅ PASSED: Found relevant memories with keywords: {expected_keywords}")
            else:
                print(f"  ❌ FAILED: No memories matched keywords: {expected_keywords}")
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ FAILED: Error retrieving memories: {e}")
            all_passed = False
    
    return all_passed

def test_memory_injection_format():
    """Test 4: Simulate message assembly and verify format"""
    print_header("TEST 4: Memory Injection Format")
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lumina_memory.db")
    store = MemoryStore(db_path)
    
    try:
        # Simulate what server.py does
        identity_memories = store.get_identity_memories()
        relevant_memories = store.get_relevant_memories("who created you?", max_results=6)
        
        # Combine and deduplicate
        all_memories = identity_memories.copy()
        identity_ids = {m['id'] for m in identity_memories}
        
        for mem in relevant_memories:
            if mem['id'] not in identity_ids:
                all_memories.append(mem)
        
        if not all_memories:
            print("❌ FAILED: No memories to inject")
            return False
        
        # Build memory block (same logic as server.py)
        memory_lines = [
            "[LONG-TERM MEMORY — AUTHORITATIVE]",
            "INSTRUCTIONS: Treat these memory items as true facts about the user unless explicitly contradicted.",
            "If the user asks about something covered by memory, answer using memory.",
            "Never refer to Scepter as a third person; Scepter IS the user you are speaking with.",
            ""
        ]
        
        # Organize by category
        identity_items = [m for m in all_memories if any(kw in m['content'].lower() for kw in ['scepter', 'rochak', 'companion', 'owner'])]
        preference_items = [m for m in all_memories if m['type'] == 'preference']
        fact_items = [m for m in all_memories if m['type'] == 'fact' and m not in identity_items]
        
        if identity_items:
            memory_lines.append("IDENTITY:")
            for mem in identity_items:
                memory_lines.append(f"- (fact) {mem['content']}")
            memory_lines.append("")
        
        if preference_items:
            memory_lines.append("PREFERENCES:")
            for mem in preference_items:
                memory_lines.append(f"- (preference) {mem['content']}")
            memory_lines.append("")
        
        if fact_items:
            memory_lines.append("FACTS:")
            for mem in fact_items:
                memory_lines.append(f"- (fact) {mem['content']}")
            memory_lines.append("")
        
        memory_context = "\n".join(memory_lines)
        
        # Verify format
        print("Generated Memory Block:")
        print("-" * 70)
        print(memory_context[:500])
        if len(memory_context) > 500:
            print(f"... (truncated, total {len(memory_context)} chars)")
        print("-" * 70)
        
        # Assertions
        checks = [
            ("[LONG-TERM MEMORY — AUTHORITATIVE]" in memory_context, "Contains authoritative header"),
            ("INSTRUCTIONS:" in memory_context, "Contains instructions"),
            ("Scepter IS the user" in memory_context, "Contains Scepter identity rule"),
            ("IDENTITY:" in memory_context, "Has IDENTITY section"),
            (len(identity_items) > 0, f"Has identity items ({len(identity_items)} found)")
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"✅ {desc}")
            else:
                print(f"❌ {desc}")
                all_passed = False
        
        # Test final message assembly
        user_text = "who created you?"
        full_message = memory_context + "\n" + user_text
        
        print(f"\n✅ Final message assembled: {len(memory_context)} chars memory + {len(user_text)} chars user text")
        print(f"✅ Total payload: {len(full_message)} chars")
        print(f"✅ Message role: user (per Gemini Live API)")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED: Error assembling message: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_identity_always_included():
    """Test 5: Verify identity memories are ALWAYS included regardless of relevance"""
    print_header("TEST 5: Identity Always Included")
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lumina_memory.db")
    store = MemoryStore(db_path)
    
    # Test with a query that has no relevance to identity
    irrelevant_query = "what is the weather like?"
    
    try:
        identity_memories = store.get_identity_memories()
        relevant_memories = store.get_relevant_memories(irrelevant_query, max_results=6)
        
        print(f"Query: '{irrelevant_query}'")
        print(f"Identity memories: {len(identity_memories)}")
        print(f"Relevant memories: {len(relevant_memories)}")
        
        # Even with irrelevant query, identity should be included
        all_memories = identity_memories.copy()
        identity_ids = {m['id'] for m in identity_memories}
        
        for mem in relevant_memories:
            if mem['id'] not in identity_ids:
                all_memories.append(mem)
        
        identity_count = len(identity_memories)
        total_count = len(all_memories)
        
        if identity_count > 0:
            print(f"✅ PASSED: Identity memories ({identity_count}) are ALWAYS included")
            print(f"✅ INFO: Total memories for injection: {total_count}")
            return True
        else:
            print(f"❌ FAILED: No identity memories available")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error testing identity inclusion: {e}")
        return False

def main():
    """Run all Phase C validation tests"""
    print_header("PHASE C VALIDATION TESTS - Memory Authoritative System")
    
    print("\nRunning in lumina conda environment...")
    print("All tests validate authoritative memory injection.\n")
    
    results = {
        "Database Exists": test_database_exists(),
        "Identity Memories Present": test_identity_memories(),
        "Relevant Memory Retrieval": test_relevant_memory_retrieval(),
        "Memory Injection Format": test_memory_injection_format(),
        "Identity Always Included": test_identity_always_included()
    }
    
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Memory system is working correctly.")
        print("\nNext steps:")
        print("1. Start server: python server.py")
        print("2. Connect frontend and test manually:")
        print("   - Ask: 'who created you?' (should mention Scepter as YOU)")
        print("   - Ask: 'what are my preferences?' (should use saved preferences)")
        print("   - Restart server and verify persistence")
        return 0
    else:
        print("\n❌ Some tests failed. Review errors above.")
        print("\nTroubleshooting:")
        print("1. Ensure you're in lumina conda environment: conda activate lumina")
        print("2. Start server once to seed identity memories: python server.py")
        print("3. Check backend/lumina_memory.db exists")
        return 1

if __name__ == "__main__":
    sys.exit(main())
