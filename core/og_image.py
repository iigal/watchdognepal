import os
import textwrap
from io import BytesIO
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

# Define paths
STATIC_DIR = os.path.join(settings.BASE_DIR, 'static')
FONT_REGULAR_PATH = os.path.join(STATIC_DIR, 'fonts', 'NotoSansDevanagari-Regular.ttf')
FONT_BOLD_PATH = os.path.join(STATIC_DIR, 'fonts', 'NotoSansDevanagari-Bold.ttf')
LOGO_PATH = os.path.join(STATIC_DIR, 'logo.jpg')

def get_font(path, size, fallback="Arial"):
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
        return ImageFont.truetype(fallback, size)
    except IOError:
        return ImageFont.load_default()

def draw_text_wrapped(draw, text, font, draw_x, draw_y, max_width, fill="white", line_spacing=10, max_lines=None):
    """Draws text wrapped within max_width and returns the bottom Y coordinate."""
    # This is a basic wrapper. TrueType formatting for Devanagari might need layout engine, 
    # but Pillow handles simple layouts okay.
    lines = []
    current_line = ""
    for word in text.replace("\n", " ").split():
        test_line = current_line + " " + word if current_line else word
        # Calculate width
        w = draw.textlength(test_line, font=font)
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
        
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1] + "..."

    y_text = draw_y
    for line in lines:
        try:
            # textbbox gives (left, top, right, bottom)
            bbox = draw.textbbox((0, 0), line, font=font)
            height = bbox[3] - bbox[1]
        except AttributeError:
            height = font.getsize(line)[1] # Fallback for older Pillow
        
        draw.text((draw_x, y_text), line, font=font, fill=fill)
        y_text += height + line_spacing
    
    return y_text

def generate_manifesto_og_image(point):
    """
    Generates a 1200x630 OG image for a ManifestoPoint.
    Returns a Pillow Image object.
    """
    # 1. Base setup
    width, height = 1200, 630
    # Background color (dark slate/navy gradient feel)
    bg_color = (15, 23, 42) # Tailwind slate-900
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Decorative gradient accent at bottom
    for i in range(10):
        # A simple gradient accent line (blue to purple)
        draw.line([(0, height - 10 + i), (width, height - 10 + i)], fill=(59, 130 + i*10, 246 - i*5))

    padding = 60

    # 2. Fonts
    font_brand = get_font(FONT_BOLD_PATH, 32)
    font_title = get_font(FONT_BOLD_PATH, 55)
    font_desc = get_font(FONT_REGULAR_PATH, 36)
    font_meta = get_font(FONT_REGULAR_PATH, 28)

    # 3. Draw Logo & Brand
    logo_size = 80
    current_y = padding
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            # Make logo circular
            mask = Image.new('L', (logo_size, logo_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)
            
            # Composite
            img.paste(logo, (padding, current_y), mask)
        except Exception:
            pass # Ignore logo errors
    
    # Brand Text
    draw.text((padding + logo_size + 20, current_y + 20), "Watchdog Nepal", font=font_brand, fill=(148, 163, 184))
    
    current_y += logo_size + 40

    # 4. Title
    title = str(point.title)
    current_y = draw_text_wrapped(draw, title, font_title, padding, current_y, 
                                  max_width=width - (padding * 2), fill="white", max_lines=3, line_spacing=15)
    current_y += 20

    # 5. Description
    if point.description:
        desc = str(point.description)
        current_y = draw_text_wrapped(draw, desc, font_desc, padding, current_y, 
                                      max_width=width - (padding * 2), fill=(148, 163, 184), max_lines=2, line_spacing=10)
        current_y += 40

    # 6. Metadata (Party, Deadline, Verified Activities)
    meta_texts = []
    
    owner = point.party.name if point.party else (point.elected_member.name if point.elected_member else "Government")
    meta_texts.append(f"🏛 {owner}")
    
    if point.calculated_deadline:
        # Avoid bs4 imports here, keep it simple, just stringifying
        meta_texts.append(f"📅 Deadline: {point.calculated_deadline.strftime('%Y-%m-%d')}")
        
    activities_count = point.verified_activities.count() if hasattr(point, 'verified_activities') else 0
    if activities_count > 0:
        meta_texts.append(f"✓ {activities_count} Verified Activities")

    meta_x = padding
    for m in meta_texts:
        draw.text((meta_x, current_y), m, font=font_meta, fill=(203, 213, 225))
        # Add spacing horizontally
        meta_x += draw.textlength(m, font=font_meta) + 40

    # 7. Progress Bar at bottom area
    current_y = height - 120
    draw.text((padding, current_y - 40), f"Implementation Progress: {point.completion_percentage}%", font=font_meta, fill="white")
    
    bar_width = width - (padding * 2)
    bar_height = 24
    
    # Background bar
    draw.rounded_rectangle([(padding, current_y), (padding + bar_width, current_y + bar_height)], 
                           radius=bar_height//2, fill=(30, 41, 59))
    
    # Foreground bar (Progress)
    progress_width = max(int(bar_width * (point.completion_percentage / 100.0)), bar_height)
    if point.completion_percentage > 0:
        draw.rounded_rectangle([(padding, current_y), (padding + progress_width, current_y + bar_height)], 
                               radius=bar_height//2, fill=(16, 185, 129)) # Emerald-500

    return img
