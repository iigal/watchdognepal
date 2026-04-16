import os
from datetime import timedelta
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

# Define paths
STATIC_DIR = os.path.join(settings.BASE_DIR, 'static')
FONT_REGULAR_PATH = os.path.join(STATIC_DIR, 'fonts', 'Mukta-Regular.ttf')
FONT_BOLD_PATH = os.path.join(STATIC_DIR, 'fonts', 'Mukta-Bold.ttf')
LOGO_PATH = os.path.join(STATIC_DIR, 'logo.jpg')

def get_font(path, size, fallback="Arial"):
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
        return ImageFont.truetype(fallback, size)
    except IOError:
        return ImageFont.load_default()

def get_latin_font(size):
    linux_fonts = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    ]
    mac_fonts = [
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf'
    ]
    for font_path in linux_fonts + mac_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("Arial", size)
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


def _get_status_ne(item):
    """Return (label, bg_color, text_color) for OG status badge."""
    from django.utils import timezone

    if item.is_completed is not None or item.completion_percentage == 100:
        return ("सम्पन्न", (220, 252, 231), (6, 95, 70))
    if item.is_partly_crossed:
        return ("आंशिक रूपमा समयसीमा नाघेको", (255, 237, 213), (146, 64, 14))
    if item.is_overdue:
        return ("समयसीमा बितिसक्यो", (254, 226, 226), (153, 27, 27))

    deadline = item.calculated_deadline
    if deadline:
        days_left = (deadline - timezone.now().date()).days
        if 0 <= days_left <= 30:
            return ("समयसीमा नजिकिँदै", (254, 243, 199), (146, 64, 14))

    if item.is_in_progress:
        return ("कार्य प्रगतिमा", (219, 234, 254), (30, 64, 175))
    return ("सुरु हुन बाँकी", (226, 232, 240), (51, 65, 85))


def _draw_badge(draw, x, y, text, font, bg, fg):
    pad_x, pad_y = 16, 10
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.rounded_rectangle(
        [(x, y), (x + w + pad_x * 2, y + h + pad_y * 2)],
        radius=22,
        fill=bg,
    )
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=fg)


def _generate_og_image(item, subtitle):
    """Shared OG image generator for manifesto/commitment."""
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Soft light gradient bands
    for i in range(height):
        tint = 255 - int(i * 0.03)
        draw.line([(0, i), (width, i)], fill=(max(240, tint), max(244, tint), 255))
    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=26, outline=(226, 232, 240), width=2)

    padding = 56
    current_y = padding

    # Fonts
    font_brand = get_font(FONT_BOLD_PATH, 38)
    font_subtitle = get_font(FONT_REGULAR_PATH, 28)
    font_title = get_font(FONT_BOLD_PATH, 62)
    font_desc = get_font(FONT_REGULAR_PATH, 36)
    font_status = get_font(FONT_BOLD_PATH, 30)
    font_meta = get_font(FONT_BOLD_PATH, 34)
    font_meta_label = get_font(FONT_REGULAR_PATH, 27)

    # Logo
    logo_size = 88
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            mask = Image.new('L', (logo_size, logo_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)
            img.paste(logo, (padding, current_y), mask)
        except Exception:
            pass

    # Top brand text (bigger and clearer)
    draw.text((padding + logo_size + 20, current_y + 8), "Watchdog Nepal", font=font_brand, fill=(15, 23, 42))
    draw.text((padding + logo_size + 22, current_y + 48), subtitle, font=font_subtitle, fill=(71, 85, 105))

    # Status badge (highlighted part in Nepali)
    status_text, status_bg, status_fg = _get_status_ne(item)
    _draw_badge(draw, width - 460, current_y + 22, status_text, font_status, status_bg, status_fg)
    current_y += logo_size + 34

    # Title
    current_y = draw_text_wrapped(
        draw,
        str(item.title),
        font_title,
        padding,
        current_y,
        max_width=width - (padding * 2),
        fill=(17, 24, 39),
        max_lines=3,
        line_spacing=14,
    )
    current_y += 10

    # Description
    if item.description:
        current_y = draw_text_wrapped(
            draw,
            str(item.description),
            font_desc,
            padding,
            current_y,
            max_width=width - (padding * 2),
            fill=(51, 65, 85),
            max_lines=2,
            line_spacing=10,
        )

    # Bottom information area (no progress bar)
    line_y = height - 170
    draw.line([(padding, line_y - 18), (width - padding, line_y - 18)], fill=(203, 213, 225), width=2)

    # Bigger deadline text
    deadline_label = "समयसीमा"
    deadline_text = "उल्लेख छैन"
    if item.calculated_deadline:
        deadline_text = item.calculated_deadline.strftime('%Y-%m-%d')
    draw.text((padding, line_y), f"{deadline_label}: {deadline_text}", font=font_meta, fill=(30, 41, 59))

    # Bigger implementation progress text
    progress_text = f"कार्यान्वयन प्रगति: {item.completion_percentage}%"
    progress_x = padding
    progress_y = line_y + 52
    draw.text((progress_x, progress_y), progress_text, font=font_meta, fill=(30, 41, 59))
    draw.text((progress_x, progress_y + 38), f"प्रगति अंश: {item.progress_fraction}", font=font_meta_label, fill=(71, 85, 105))

    # Owner text on the right
    owner = item.party.name if item.party else (item.elected_member.name if item.elected_member else "Government")
    owner_label = f"जिम्मेवार: {owner}"
    owner_bbox = draw.textbbox((0, 0), owner_label, font=font_meta_label)
    owner_w = owner_bbox[2] - owner_bbox[0]
    draw.text((width - padding - owner_w, progress_y + 38), owner_label, font=font_meta_label, fill=(71, 85, 105))

    return img

def generate_manifesto_og_image(point):
    """
    Generates a 1200x630 OG image for a ManifestoPoint.
    Returns a Pillow Image object.
    """
    return _generate_og_image(point, "Manifesto")


def generate_commitment_og_image(commitment):
    """
    Generates a 1200x630 OG image for a Commitment.
    Uses a violet/indigo color scheme to distinguish from manifesto images.
    Returns a Pillow Image object.
    """
    return _generate_og_image(commitment, "Commitment")
