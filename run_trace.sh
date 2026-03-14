#!/bin/bash

echo "🔬 AXR Component Testing"
echo "========================"
echo ""

# Test 1: Planner
echo "📋 Test 1: Planner Agent"
python test_planner.py
echo ""

# Test 2: Verifier
echo "✅ Test 2: Verifier Agent"
python test_verifier.py
echo ""

# Test 3: Scheduler
echo "⏰ Test 3: Scheduler"
python test_scheduler.py
echo ""

# Test 4: Tools
echo "🔧 Test 4: Tool Router"
python test_tools.py
echo ""

# Test 5: Full Integration
echo "🔄 Test 5: Full Integration"
python test_integration.py
echo ""

echo "✨ All tests complete!"