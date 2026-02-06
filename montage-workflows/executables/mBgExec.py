#!/usr/bin/env python3
"""mBgExec - Apply background corrections."""

import sys
import time
import random
from datetime import datetime

def main():
    print(f"[{datetime.now()}] mBgExec: Applying background correction")
    time.sleep(random.uniform(0.5, 1.5))
    
    if len(sys.argv) >= 4:
        with open(sys.argv[3], 'w') as f:
            f.write(f"CORRECTED: {datetime.now()}\n")
    
    print(f"[{datetime.now()}] mBgExec: Complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())
