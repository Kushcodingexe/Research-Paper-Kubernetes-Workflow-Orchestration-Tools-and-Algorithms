#!/usr/bin/env python3
"""mJPEG - Convert FITS to JPEG."""

import sys
import time
from datetime import datetime

def main():
    print(f"[{datetime.now()}] mJPEG: Converting to JPEG")
    time.sleep(0.5)
    
    if len(sys.argv) >= 3:
        with open(sys.argv[2], 'w') as f:
            f.write(f"JPEG: {datetime.now()}\n")
    
    print(f"[{datetime.now()}] mJPEG: Complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())
