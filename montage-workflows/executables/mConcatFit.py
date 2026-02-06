#!/usr/bin/env python3
"""mConcatFit - Concatenate fit files."""

import sys
import time
from datetime import datetime

def main():
    print(f"[{datetime.now()}] mConcatFit: Concatenating fits")
    time.sleep(0.5)
    
    # Find output file from args
    output_idx = sys.argv.index('-o') + 1 if '-o' in sys.argv else -1
    if output_idx > 0 and output_idx < len(sys.argv):
        with open(sys.argv[output_idx], 'w') as f:
            f.write(f"CONCAT: {datetime.now()}\n")
    
    print(f"[{datetime.now()}] mConcatFit: Complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())
