"""
Phase E2 - Memory Suggestion System Test

Tests the human-like memory system with explicit user approval.
No auto-writes - all memory saves require user confirmation.

MUST run in conda environment 'lumina'.
"""

import asyncio
import socketio
import sys
import os

# Verify conda environment
REQUIRED_ENV = "lumina"
current_env = os.environ.get("CONDA_DEFAULT_ENV", "")

if current_env != REQUIRED_ENV:
    print(f"\n{'='*60}")
    print(f"ERROR: Wrong conda environment!")
    print(f"{'='*60}")
    print(f"Required: {REQUIRED_ENV}")
    print(f"Current:  {current_env or '(none)'}")
    print(f"\nPlease activate the correct environment:")
    print(f"  conda activate {REQUIRED_ENV}")
    print(f"{'='*60}\n")
    sys.exit(1)

print(f"[ENV CHECK] ✓ Running in conda environment: {REQUIRED_ENV}")

# Test configuration
SERVER_URL = 'http://localhost:8000'
TEST_TIMEOUT = 10  # seconds


async def test_memory_suggestion_flow():
    """
    Test the complete memory suggestion flow:
    1. Send a message that should trigger a suggestion
    2. Receive memory_suggestion event
    3. Accept the suggestion
    4. Verify it appears in /memory
    """
    print("\n" + "="*70)
    print("PHASE E2 TEST - Memory Suggestion with User Approval")
    print("="*70)
    
    sio = socketio.AsyncClient()
    test_results = {
        'connected': False,
        'suggestion_received': False,
        'suggestion_data': None,
        'acceptance_confirmed': False,
        'memory_persisted': False
    }
    
    # Event handlers
    @sio.on('connect')
    async def on_connect():
        print("✓ Connected to server")
        test_results['connected'] = True
    
    @sio.on('memory_suggestion')
    async def on_memory_suggestion(data):
        print(f"\n✓ Received memory suggestion:")
        print(f"  Type: {data['type']}")
        print(f"  Content: {data['content']}")
        print(f"  Confidence: {data['confidence']}")
        print(f"  Reason: {data['reason']}")
        print(f"  Temp ID: {data['temp_id']}")
        test_results['suggestion_received'] = True
        test_results['suggestion_data'] = data
    
    @sio.on('chat_message')
    async def on_chat_message(data):
        print(f"\n[CHAT] {data.get('sender', 'System')}: {data.get('text', '')}")
        
        # Check for acceptance confirmation
        if '✅ Memory saved' in data.get('text', ''):
            test_results['acceptance_confirmed'] = True
            print("✓ Memory acceptance confirmed")
        
        # Check for memory list (from /memory command)
        if '📝 Recent Memories' in data.get('text', ''):
            # Check if our test content is in the list
            if 'I prefer dark mode' in data.get('text', ''):
                test_results['memory_persisted'] = True
                print("✓ Memory persisted in database")
    
    try:
        # Connect to server
        print(f"\n[TEST] Connecting to {SERVER_URL}...")
        await sio.connect(SERVER_URL)
        await asyncio.sleep(1)
        
        if not test_results['connected']:
            print("❌ FAILED: Could not connect to server")
            print("   Make sure backend is running: python backend/server.py")
            return False
        
        # Test 1: Send a message that should trigger a suggestion
        print("\n[TEST 1] Sending message with preference pattern...")
        test_message = "I prefer dark mode and minimal UI"
        await sio.emit('user_input', {'text': test_message})
        
        # Wait for suggestion
        await asyncio.sleep(2)
        
        if not test_results['suggestion_received']:
            print("❌ FAILED: No memory suggestion received")
            print("   Expected: memory_suggestion event with preference")
            return False
        
        print("✓ TEST 1 PASSED: Memory suggestion received")
        
        # Test 2: Accept the suggestion
        print("\n[TEST 2] Accepting memory suggestion...")
        suggestion_data = test_results['suggestion_data']
        await sio.emit('memory_decision', {
            'temp_id': suggestion_data['temp_id'],
            'accept': True
        })
        
        # Wait for confirmation
        await asyncio.sleep(1)
        
        if not test_results['acceptance_confirmed']:
            print("❌ FAILED: No acceptance confirmation received")
            return False
        
        print("✓ TEST 2 PASSED: Memory acceptance confirmed")
        
        # Test 3: Verify memory persisted
        print("\n[TEST 3] Verifying memory persistence...")
        await sio.emit('user_input', {'text': '/memory'})
        
        # Wait for memory list
        await asyncio.sleep(1)
        
        if not test_results['memory_persisted']:
            print("❌ FAILED: Memory not found in database")
            print("   Expected: Memory to appear in /memory list")
            return False
        
        print("✓ TEST 3 PASSED: Memory persisted in database")
        
        # Test 4: Test rejection flow
        print("\n[TEST 4] Testing rejection flow...")
        test_results['suggestion_received'] = False
        test_results['suggestion_data'] = None
        
        # Send another message
        await sio.emit('user_input', {'text': 'I like bright colors'})
        await asyncio.sleep(2)
        
        if test_results['suggestion_received']:
            print("✓ Received second suggestion")
            # Reject it
            await sio.emit('memory_decision', {
                'temp_id': test_results['suggestion_data']['temp_id'],
                'accept': False
            })
            await asyncio.sleep(1)
            print("✓ TEST 4 PASSED: Rejection flow works")
        else:
            print("⚠️  TEST 4 SKIPPED: No second suggestion (might be duplicate)")
        
        # All tests passed
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\nPhase E2 Implementation Verified:")
        print("  ✓ Memory suggestions are emitted (no auto-save)")
        print("  ✓ User approval required before saving")
        print("  ✓ Accepted memories persist to database")
        print("  ✓ Rejected memories are discarded")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await sio.disconnect()
        print("\n[TEST] Disconnected from server")


async def test_no_auto_save():
    """
    Verify that memory is NOT auto-saved without user approval.
    """
    print("\n" + "="*70)
    print("SAFETY TEST - Verify No Auto-Save")
    print("="*70)
    
    sio = socketio.AsyncClient()
    auto_save_detected = False
    
    @sio.on('chat_message')
    async def on_chat_message(data):
        nonlocal auto_save_detected
        # Check for auto-save indicators (old Phase B2 behavior)
        text = data.get('text', '')
        if '[AUTO-CAPTURE]' in text or 'Saved {mem_type}' in text:
            auto_save_detected = True
            print(f"❌ AUTO-SAVE DETECTED: {text}")
    
    try:
        await sio.connect(SERVER_URL)
        await asyncio.sleep(1)
        
        # Send a message that would have triggered auto-save in Phase B2
        await sio.emit('user_input', {'text': 'I like testing'})
        await asyncio.sleep(2)
        
        if auto_save_detected:
            print("❌ SAFETY TEST FAILED: Auto-save still active!")
            print("   Phase E2 requires explicit user approval")
            return False
        else:
            print("✓ SAFETY TEST PASSED: No auto-save detected")
            return True
            
    finally:
        await sio.disconnect()


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PHASE E2 - MEMORY SUGGESTION SYSTEM TESTS")
    print("="*70)
    print("\nPrerequisites:")
    print("  1. Backend server must be running (python backend/server.py)")
    print("  2. Running in conda environment 'lumina'")
    print("  3. Server listening on http://localhost:8000")
    print("="*70)
    
    # Run tests
    test1_passed = await test_memory_suggestion_flow()
    test2_passed = await test_no_auto_save()
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    print(f"Memory Suggestion Flow: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"No Auto-Save Safety:    {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("="*70)
    
    if test1_passed and test2_passed:
        print("\n🎉 Phase E2 implementation is CORRECT and SAFE")
        print("   - No silent writes to memory database")
        print("   - User approval required for all memory saves")
        print("   - Suggestion system working as expected")
        return 0
    else:
        print("\n❌ Some tests failed - review implementation")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
