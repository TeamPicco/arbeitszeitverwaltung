#!/usr/bin/env python3
"""
Generiert PWA-Icons aus dem Piccolo-Logo
"""

from PIL import Image
import os

# Pfade
logo_path = "assets/crewbase_logo_optimized.png"
icons_dir = "assets/icons"

# Erstelle icons-Verzeichnis falls nicht vorhanden
os.makedirs(icons_dir, exist_ok=True)

# Lade das Logo
logo = Image.open(logo_path)

# Konvertiere zu RGBA falls nötig
if logo.mode != 'RGBA':
    logo = logo.convert('RGBA')

# Icon-Größen für PWA
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

print("Generiere Icons...")

for size in sizes:
    # Erstelle quadratisches Icon
    icon = logo.resize((size, size), Image.Resampling.LANCZOS)
    
    # Speichere als PNG
    output_path = os.path.join(icons_dir, f"icon-{size}x{size}.png")
    icon.save(output_path, "PNG")
    print(f"✓ {output_path}")

# Erstelle auch apple-touch-icon
apple_icon = logo.resize((180, 180), Image.Resampling.LANCZOS)
apple_icon.save(os.path.join(icons_dir, "apple-touch-icon.png"), "PNG")
print(f"✓ {os.path.join(icons_dir, 'apple-touch-icon.png')}")

# Erstelle favicon
favicon = logo.resize((32, 32), Image.Resampling.LANCZOS)
favicon.save("assets/favicon.ico", "ICO")
print(f"✓ assets/favicon.ico")

print("\n✅ Alle Icons erfolgreich generiert!")
