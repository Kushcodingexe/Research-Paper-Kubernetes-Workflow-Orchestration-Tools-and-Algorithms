#!/usr/bin/env python3
"""
Rack Resiliency Simulation Script for Pegasus
Simulates health checks, node failures, and rack failures.
"""

import sys
import time
import random
import os
from datetime import datetime

def health_check(stabilization_time=10):
    """Simulate a health check."""
    print(f"[{datetime.now()}] Starting health check...")
    time.sleep(stabilization_time)
    print(f"[{datetime.now()}] Health check complete. All systems operational.")
    return 0

def node_failure(node_name, stabilization_time=30):
    """Simulate a node failure."""
    print(f"[{datetime.now()}] Simulating node failure: {node_name}")
    time.sleep(stabilization_time / 2)
    print(f"[{datetime.now()}] Node {node_name} marked as failed")
    time.sleep(stabilization_time / 2)
    print(f"[{datetime.now()}] Node {node_name} recovered")
    return 0

def rack_failure(rack_name, stabilization_time=30):
    """Simulate a rack failure."""
    print(f"[{datetime.now()}] Simulating rack failure: {rack_name}")
    time.sleep(stabilization_time / 2)
    print(f"[{datetime.now()}] Rack {rack_name} marked as failed")
    time.sleep(stabilization_time / 2)
    print(f"[{datetime.now()}] Rack {rack_name} recovered")
    return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: rack_resiliency_sim.py <command> [args...]")
        print("Commands: health-check, node-failure, rack-failure")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Parse stabilization time from args
    stab_time = 10
    for arg in sys.argv[2:]:
        if arg.startswith('--stabilization-time='):
            stab_time = int(arg.split('=')[1])
    
    if command == 'health-check':
        sys.exit(health_check(stab_time))
    elif command == 'node-failure':
        node_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'worker-001'
        sys.exit(node_failure(node_name, stab_time))
    elif command == 'rack-failure':
        rack_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'R1'
        sys.exit(rack_failure(rack_name, stab_time))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
