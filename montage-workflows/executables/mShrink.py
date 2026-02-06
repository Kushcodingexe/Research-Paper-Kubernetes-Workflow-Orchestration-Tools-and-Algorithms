#!/usr/bin/env python3
"""mShrink - Create thumbnail of mosaic."""

import sys
import time
from datetime import datetime

def main():
    print(f"[{datetime.now()}] mShrink: Creating thumbnail")
    time.sleep(0.5)
    
    if len(sys.argv) >= 3:
        with open(sys.argv[2], 'w') as f:
            f.write(f"THUMBNAIL: {datetime.now()}\n")
    
    print(f"[{datetime.now()}] mShrink: Complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())
