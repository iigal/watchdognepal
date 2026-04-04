"""
Branded Image Generator for Watchdog Nepal Social Posts
=======================================================
Generates Instagram-ready images with two template options:
  Template A (Keyword Highlight): Text over dimmed image, important words highlighted yellow
  Template B (Red Box Title): Title in red box, description below

Global branding: Logo (top-left) + Nepali Date (top-right)
"""
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.conf import settings
from django.core.files.base import ContentFile

STATIC_DIR = os.path.join(settings.BASE_DIR, 'static')
FONT_REGULAR = os.path.join(STATIC_DIR, 'fonts', 'NotoSansDevanagari-Regular.ttf')
FONT_BOLD = os.path.join(STATIC_DIR, 'fonts', 'NotoSansDevanagari-Bold.ttf')
LOGO_PATH = os.path.join(STATIC_DIR, 'logo.jpg')

# ── Dimension Presets ─────────────────────────────────────────────────
DIMENSIONS = {
    '1:1': (1080, 1080),
    '4:5': (1080, 1350),
}


def _get_font(path, size):
    """Load a TrueType font with fallback."""
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    
    # Fallbacks
    for fallback in ['/System/Library/Fonts/Helvetica.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if os.path.exists(fallback):
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:
                pass
    
    return ImageFont.load_default()


def _get_nepali_date_string():
    """Get today's Nepali date as a formatted string."""
    try:
        import nepali_datetime
        today = nepali_datetime.date.NepaliDate.today()
        return today.strftime('%K-%N-%D')  # e.g., २०८२-१२-२२
    except Exception:
        from datetime import date
        return date.today().strftime('%Y-%m-%d')


def _paste_logo(img, padding=40, size=70):
    """Paste circular logo at top-left corner."""
    if not os.path.exists(LOGO_PATH):
        return
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = logo.resize((size, size), Image.Resampling.LANCZOS)
        
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        
        img.paste(logo, (padding, padding), mask)
    except Exception:
        pass


def _draw_nepali_date(draw, img_width, padding=40, y=45):
    """Draw Nepali date at top-right corner."""
    font = _get_font(FONT_REGULAR, 28)
    date_str = _get_nepali_date_string()
    
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    
    x = img_width - padding - text_width
    
    # Draw semi-transparent background pill
    pill_padding = 10
    draw.rounded_rectangle(
        [(x - pill_padding, y - pill_padding // 2),
         (x + text_width + pill_padding, y + (bbox[3] - bbox[1]) + pill_padding // 2)],
        radius=12,
        fill=(0, 0, 0, 150)
    )
    draw.text((x, y), date_str, font=font, fill="white")


def _word_wrap(draw, text, font, max_width):
    """Break text into lines that fit within max_width."""
    words = text.replace('\n', ' ').split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        w = draw.textlength(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_template_a(original_image_path, title, keywords_str, aspect_ratio='1:1'):
    """
    Template A — Keyword Highlight
    Background: dimmed user image
    Title overlaid with keywords highlighted in yellow boxes
    """
    width, height = DIMENSIONS.get(aspect_ratio, (1080, 1080))
    
    # Load and resize background
    bg = Image.open(original_image_path).convert("RGBA")
    bg = bg.resize((width, height), Image.Resampling.LANCZOS)
    
    # Darken the background
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 160))
    bg = Image.alpha_composite(bg, overlay)
    
    # Convert to RGB for drawing
    img = bg.convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # Branding
    _paste_logo(img)
    
    # For Nepali date we need RGBA temp
    temp = img.convert('RGBA')
    temp_draw = ImageDraw.Draw(temp)
    _draw_nepali_date(temp_draw, width)
    img = temp.convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # Title with keyword highlighting
    padding = 60
    font = _get_font(FONT_BOLD, 52)
    keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()] if keywords_str else []
    
    lines = _word_wrap(draw, title, font, width - padding * 2)
    
    # Center vertically
    line_height = 70
    total_text_height = len(lines) * line_height
    start_y = (height - total_text_height) // 2
    
    for i, line in enumerate(lines):
        y = start_y + i * line_height
        
        if not keywords:
            # No keywords — just draw the line centered
            line_w = draw.textlength(line, font=font)
            x = (width - line_w) // 2
            draw.text((x, y), line, font=font, fill="white")
        else:
            # Draw word by word, highlighting keywords
            words = line.split()
            # Calculate total line width for centering
            total_w = sum(draw.textlength(w, font=font) for w in words)
            total_w += draw.textlength(' ', font=font) * (len(words) - 1)
            x = (width - total_w) // 2
            
            space_w = draw.textlength(' ', font=font)
            for word in words:
                word_w = draw.textlength(word, font=font)
                bbox = draw.textbbox((x, y), word, font=font)
                word_h = bbox[3] - bbox[1]
                
                if word.strip('.,!?:;').lower() in keywords:
                    # Yellow highlight box
                    highlight_pad = 6
                    draw.rounded_rectangle(
                        [(x - highlight_pad, y - highlight_pad),
                         (x + word_w + highlight_pad, y + word_h + highlight_pad)],
                        radius=4,
                        fill=(250, 204, 21)  # Yellow
                    )
                    draw.text((x, y), word, font=font, fill=(15, 23, 42))  # Dark text
                else:
                    draw.text((x, y), word, font=font, fill="white")
                
                x += word_w + space_w
    
    return img


def generate_template_b(original_image_path, title, description, aspect_ratio='1:1'):
    """
    Template B — Red Box Title
    Background: dimmed user image
    Title in solid red box, description in plain text below
    """
    width, height = DIMENSIONS.get(aspect_ratio, (1080, 1080))
    
    # Load and resize background
    bg = Image.open(original_image_path).convert("RGBA")
    bg = bg.resize((width, height), Image.Resampling.LANCZOS)
    
    # Light darken
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 120))
    bg = Image.alpha_composite(bg, overlay)
    
    img = bg.convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # Branding
    _paste_logo(img)
    
    temp = img.convert('RGBA')
    temp_draw = ImageDraw.Draw(temp)
    _draw_nepali_date(temp_draw, width)
    img = temp.convert('RGB')
    draw = ImageDraw.Draw(img)
    
    padding = 60
    font_title = _get_font(FONT_BOLD, 48)
    font_desc = _get_font(FONT_REGULAR, 32)
    
    # Title lines
    title_lines = _word_wrap(draw, title, font_title, width - padding * 2 - 40)
    
    # Calculate red box dimensions
    line_h = 65
    box_text_height = len(title_lines) * line_h + 20
    box_y = height // 2 - box_text_height // 2
    
    # Draw red box
    box_padding = 30
    draw.rounded_rectangle(
        [(padding, box_y - box_padding),
         (width - padding, box_y + box_text_height + box_padding)],
        radius=12,
        fill=(220, 38, 38)  # Red-600
    )
    
    # Draw title inside red box
    for i, line in enumerate(title_lines):
        line_w = draw.textlength(line, font=font_title)
        x = (width - line_w) // 2
        y = box_y + i * line_h + 10
        draw.text((x, y), line, font=font_title, fill="white")
    
    # Draw description below red box
    if description:
        desc_y = box_y + box_text_height + box_padding + 30
        desc_lines = _word_wrap(draw, description, font_desc, width - padding * 2)
        
        for i, line in enumerate(desc_lines[:3]):  # Max 3 lines
            line_w = draw.textlength(line, font=font_desc)
            x = (width - line_w) // 2
            draw.text((x, desc_y + i * 45), line, font=font_desc, fill="white")
    
    return img


def generate_branded_image(post):
    """
    Main entry point: generates a branded image for a SocialPost instance.
    Saves the result to post.branded_image.
    
    Args:
        post: SocialPost instance with original_image set
    
    Returns:
        bool: True if successful
    """
    if not post.original_image:
        return False
    
    image_path = post.original_image.path
    
    if post.template_choice == 'keyword_highlight':
        img = generate_template_a(
            image_path, post.title, post.keywords, post.aspect_ratio
        )
    else:
        img = generate_template_b(
            image_path, post.title, post.description, post.aspect_ratio
        )
    
    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format='PNG', quality=95)
    buffer.seek(0)
    
    # Save to model
    filename = f"branded_{post.pk}_{post.template_choice}.png"
    post.branded_image.save(filename, ContentFile(buffer.read()), save=True)
    
    return True
