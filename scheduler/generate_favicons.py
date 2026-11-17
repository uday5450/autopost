import os
import math
from PIL import Image, ImageDraw

def create_gradient_image(size, start_color, end_color):
    """Create a 135-degree diagonal gradient image."""
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Render line by line diagonally
    for y in range(size):
        for x in range(size):
            # Distance along diagonal (0.0 to 1.0)
            ratio = (x + y) / (2.0 * size)
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            base.putpixel((x, y), (r, g, b, 255))
    return base

def generate_feedbridge_icon(hires_size=1024):
    """Generate high-res master icon with supersampling and modern aesthetics."""
    # Start with transparent canvas
    img = Image.new("RGBA", (hires_size, hires_size), (0, 0, 0, 0))
    
    # Rounded rectangle bounds (with 5% margin for elegant breathing room)
    margin = int(hires_size * 0.04) # 40px
    radius = int(hires_size * 0.22) # 225px squircle corner radius
    rect_box = [margin, margin, hires_size - margin, hires_size - margin]
    
    # 1. Create squircle mask
    mask = Image.new("L", (hires_size, hires_size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle(rect_box, radius=radius, fill=255)
    
    # 2. Diagonal Emerald Gradient (#22c55e -> #059669)
    # Bright FeedBridge emerald to rich deep green
    start_rgb = (34, 197, 94)   # #22c55e
    end_rgb = (5, 150, 105)     # #059669
    
    gradient_img = Image.new("RGBA", (hires_size, hires_size), (0, 0, 0, 0))
    draw_grad = ImageDraw.Draw(gradient_img)
    
    # Draw diagonal gradient efficiently
    for i in range(hires_size * 2):
        t = i / (hires_size * 2)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)
        # Line from (i, 0) to (0, i)
        draw_grad.line([(i, 0), (0, i)], fill=(r, g, b, 255), width=2)
    
    # Paste gradient using squircle mask
    img.paste(gradient_img, (0, 0), mask)
    
    # 3. Inner border highlight (1.5px subtle glass bevel)
    draw = ImageDraw.Draw(img)
    bevel_width = max(2, int(hires_size * 0.008))
    draw.rounded_rectangle(rect_box, radius=radius, outline=(255, 255, 255, 45), width=bevel_width)
    
    # 4. FeedBridge 3-Layer Stack Brand Mark
    # Center = (512, 512), Icon Area = 560x560
    center_x = hires_size / 2.0
    center_y = hires_size / 2.0
    
    # Coordinate mapper from 24x24 viewBox to hires pixels
    # In 24x24 viewBox:
    # Top rhomboid: (12, 2.5) -> (2.5, 7.5) -> (12, 12.5) -> (21.5, 7.5) -> close
    # Middle chevron: (2.5, 12.5) -> (12, 17.5) -> (21.5, 12.5)
    # Bottom chevron: (2.5, 17.5) -> (12, 22.5) -> (21.5, 17.5)
    
    scale = (hires_size * 0.54) / 19.0  # ~29px per viewBox unit
    
    def pt(vx, vy):
        px = center_x + (vx - 12.0) * scale
        py = center_y + (vy - 12.5) * scale
        return (px, py)
    
    stroke_w = int(scale * 2.3) # ~66px stroke
    
    # Top diamond points
    top_poly = [pt(12, 2.5), pt(21.5, 7.5), pt(12, 12.5), pt(2.5, 7.5)]
    
    # Subtle translucent fill for top surface
    overlay = Image.new("RGBA", (hires_size, hires_size), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.polygon(top_poly, fill=(255, 255, 255, 40))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # Top diamond outline with rounded corners
    draw.line([top_poly[0], top_poly[1], top_poly[2], top_poly[3], top_poly[0]], 
              fill=(255, 255, 255, 255), width=stroke_w, joint="curve")
    
    # Middle chevron
    mid_line = [pt(2.5, 12.5), pt(12, 17.5), pt(21.5, 12.5)]
    draw.line(mid_line, fill=(255, 255, 255, 255), width=stroke_w, joint="curve")
    # Draw rounded end caps for middle line
    cap_r = stroke_w // 2
    for p in [mid_line[0], mid_line[-1]]:
        draw.ellipse([p[0]-cap_r, p[1]-cap_r, p[0]+cap_r, p[1]+cap_r], fill=(255, 255, 255, 255))
        
    # Bottom chevron
    bot_line = [pt(2.5, 17.5), pt(12, 22.5), pt(21.5, 17.5)]
    draw.line(bot_line, fill=(255, 255, 255, 255), width=stroke_w, joint="curve")
    # Draw rounded end caps for bottom line
    for p in [bot_line[0], bot_line[-1]]:
        draw.ellipse([p[0]-cap_r, p[1]-cap_r, p[0]+cap_r, p[1]+cap_r], fill=(255, 255, 255, 255))
        
    return img

def generate_svg():
    """Generate resolution-independent modern SVG favicon with dark/light mode optimization."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <defs>
    <linearGradient id="fbGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22c55e"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
    <filter id="fbShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="1" stdDeviation="0.8" flood-color="#022c22" flood-opacity="0.25"/>
    </filter>
  </defs>

  <!-- Squircle Base with Emerald Gradient -->
  <rect x="1" y="1" width="30" height="30" rx="7" fill="url(#fbGradient)"/>
  
  <!-- Subtle inner bevel highlight -->
  <rect x="1" y="1" width="30" height="30" rx="7" fill="none" stroke="#ffffff" stroke-width="0.75" stroke-opacity="0.22"/>

  <!-- FeedBridge Broadcast Stack -->
  <g filter="url(#fbShadow)">
    <!-- Top Layer Fill (Translucent 3D plane) -->
    <polygon points="16,5 26,10 16,15 6,10" fill="#ffffff" fill-opacity="0.18"/>
    
    <!-- Top Layer Stroke -->
    <polygon points="16,5 26,10 16,15 6,10" fill="none" stroke="#ffffff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
    
    <!-- Middle Layer -->
    <polyline points="6,15.5 16,20.5 26,15.5" fill="none" stroke="#ffffff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
    
    <!-- Bottom Layer -->
    <polyline points="6,21 16,26 26,21" fill="none" stroke="#ffffff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
'''

def main():
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'scheduler', 'images'))
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"Generating favicons in: {target_dir}")
    
    # 1. Write SVG Favicon
    svg_path = os.path.join(target_dir, 'favicon.svg')
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(generate_svg())
    print(f"✓ Generated: favicon.svg")
    
    # Also save favicon.svg in static root
    static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'scheduler'))
    with open(os.path.join(static_root, 'favicon.svg'), 'w', encoding='utf-8') as f:
        f.write(generate_svg())
    
    # 2. Generate Master 1024x1024 Icon
    print("Rendering high-res master 1024x1024 icon...")
    master = generate_feedbridge_icon(1024)
    
    # Sizes to generate
    sizes = {
        'favicon-16x16.png': 16,
        'favicon-32x32.png': 32,
        'favicon-48x48.png': 48,
        'apple-touch-icon.png': 180,
        'android-chrome-192x192.png': 192,
        'android-chrome-512x512.png': 512,
    }
    
    ico_images = []
    
    for filename, s in sizes.items():
        # High quality downsampling using Lanczos
        resized = master.resize((s, s), Image.Resampling.LANCZOS)
        out_path = os.path.join(target_dir, filename)
        resized.save(out_path, format="PNG", optimize=True)
        print(f"✓ Generated: {filename} ({s}x{s})")
        
        # Collect for ICO packaging
        if s in [16, 32, 48]:
            ico_images.append(resized)
            
    # Also create 64x64 for ICO
    img_64 = master.resize((64, 64), Image.Resampling.LANCZOS)
    ico_images.append(img_64)
    
    # 3. Generate multi-resolution favicon.ico
    # Windows/Browsers prefer ICO with 16, 32, 48, 64
    ico_path_images = os.path.join(target_dir, 'favicon.ico')
    ico_path_root = os.path.join(static_root, 'favicon.ico')
    
    # Primary 32x32 image saves all sizes
    img_32 = master.resize((32, 32), Image.Resampling.LANCZOS)
    img_32.save(ico_path_images, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    img_32.save(ico_path_root, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"✓ Generated: favicon.ico (multi-resolution 16, 32, 48, 64)")
    
    # 4. Generate Web Manifest
    manifest_content = '''{
  "name": "FeedBridge — Social Media Automation & Scheduler",
  "short_name": "FeedBridge",
  "description": "Schedule once. Publish everywhere. Cross-post automatically across Instagram, YouTube, TikTok, X, LinkedIn, Facebook, and Pinterest.",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#07090e",
  "theme_color": "#22c55e",
  "icons": [
    {
      "src": "/static/scheduler/images/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/scheduler/images/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/static/scheduler/images/favicon.svg",
      "sizes": "any",
      "type": "image/svg+xml"
    }
  ]
}
'''
    manifest_path = os.path.join(static_root, 'site.webmanifest')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    print(f"✓ Generated: site.webmanifest")
    
    print("\nAll favicon and app icon assets generated successfully!")

if __name__ == "__main__":
    main()
