#!/bin/bash
# Run visualization tests separately to avoid async event loop conflicts
# All tests pass when run individually but fail when run together due to pytest-asyncio issues

echo "Running PM Agent Visualization Tests..."
echo "======================================"

total_passed=0
total_tests=0

# Run each test file separately
for test_file in test_conversation_stream.py test_decision_visualizer.py test_health_monitor.py test_knowledge_graph.py test_ui_server.py test_visualization_integration.py; do
    echo ""
    echo "Running $test_file..."
    
    # Run the test and capture output
    output=$(python -m pytest tests/unit/visualization/$test_file -v 2>&1)
    
    # Extract passed/failed counts
    if echo "$output" | grep -q "passed"; then
        passed=$(echo "$output" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+")
        total=$(echo "$output" | grep -oE "collected [0-9]+ items" | grep -oE "[0-9]+")
        
        echo "✓ $test_file: $passed/$total tests passed"
        
        total_passed=$((total_passed + passed))
        total_tests=$((total_tests + total))
    else
        echo "✗ $test_file: Failed to run"
    fi
done

echo ""
echo "======================================"
echo "Total: $total_passed/$total_tests tests passed"

if [ $total_passed -eq $total_tests ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi