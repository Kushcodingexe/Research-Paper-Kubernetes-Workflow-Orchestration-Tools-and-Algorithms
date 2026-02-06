#!/usr/bin/env python3
"""
mDiffFit Simulator - Compute difference between overlapping images.
"""

import sys
import time
import random
from datetime import datetime

def main():
    print(f"[{datetime.now()}] mDiffFit: Computing difference")
    time.sleep(random.uniform(0.5, 2))
    
    if len(sys.argv) >= 5:
        with open(sys.argv[3], 'w') as f:
            f.write(f"DIFF: {datetime.now()}\n")
        with open(sys.argv[4], 'w') as f:
            f.write(f"FIT: a=0.1 b=0.2 c=0.3\n")
    
    print(f"[{datetime.now()}] mDiffFit: Complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())
