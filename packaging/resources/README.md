# Corall App Resources

## Application Icon

To create a macOS `.icns` icon file:

### Option 1: Using an existing image

1. Start with a 1024x1024 PNG image named `icon.png`
2. Run the following commands:

```bash
mkdir corall.iconset
sips -z 16 16     icon.png --out corall.iconset/icon_16x16.png
sips -z 32 32     icon.png --out corall.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out corall.iconset/icon_32x32.png
sips -z 64 64     icon.png --out corall.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out corall.iconset/icon_128x128.png
sips -z 256 256   icon.png --out corall.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out corall.iconset/icon_256x256.png
sips -z 512 512   icon.png --out corall.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out corall.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out corall.iconset/icon_512x512@2x.png
iconutil -c icns corall.iconset
rm -rf corall.iconset
```

3. Move `corall.icns` to this directory

### Option 2: Generate a placeholder icon

Run this Python script to generate a simple placeholder icon:

```python
# Requires Pillow: pip install Pillow
from PIL import Image, ImageDraw, ImageFont

size = 1024
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background circle
draw.ellipse([50, 50, size-50, size-50], fill='#6366f1')

# Text
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 400)
except:
    font = ImageFont.load_default()

draw.text((size//2, size//2), 'C', fill='white', font=font, anchor='mm')
img.save('icon.png')
```

Then follow Option 1 to convert to `.icns`.

## Windows Icon

For Windows, create a `.ico` file with multiple sizes (16, 32, 48, 256).
Use ImageMagick or an online converter:

```bash
convert icon.png -define icon:auto-resize=256,128,64,48,32,16 corall.ico
```
