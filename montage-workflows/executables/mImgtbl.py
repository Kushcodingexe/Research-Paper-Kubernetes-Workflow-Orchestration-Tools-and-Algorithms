#!/usr/bin/env python3
"""mImgtbl - Generate image metadata table."""

import sys
import time
from datetime import datetime

def main():
    print(f"[{datetime.now()}] mImgtbl: Generating image table")
    time.sleep(0.5)
    
    # Find -t flag for count
    n_images = 16
    if '-t' in sys.argv:
        idx = sys.argv.index('-t') + 1
        if idx < len(sys.argv):
            n_images = int(sys.argv[idx])
    
    # Output file is last arg
    output_file = sys.argv[-1]
    with open(output_file, 'w') as f:
        f.write(f"| fname | crval1 | crval2 | naxis1 | naxis2 |\n")
        for i in range(n_images):
            f.write(f"| proj_{i:03d}.fits | {i*0.1:.2f} | {i*0.1:.2f} | 512 | 512 |\n")
    
    print(f"[{datetime.now()}] mImgtbl: Complete ({n_images} images)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
