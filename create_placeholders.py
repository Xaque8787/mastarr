#!/usr/bin/env python3
"""Create placeholder images for blueprints"""

import os

# Create a minimal 1x1 transparent PNG (67 bytes)
png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

# Ensure directory exists
os.makedirs('static/images', exist_ok=True)

# Write jellyfin.png
with open('static/images/jellyfin.png', 'wb') as f:
    f.write(png_data)
print('✓ Created static/images/jellyfin.png')

# Write placeholder.png
with open('static/images/placeholder.png', 'wb') as f:
    f.write(png_data)
print('✓ Created static/images/placeholder.png')

print('\nPlaceholder images created successfully!')
