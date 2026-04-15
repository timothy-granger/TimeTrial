"""Generate a printable QR code for the live results page.

Usage:
    python -m timetrial.tools.generate_qr [url] [output_file]

Defaults:
    url: https://timothy-granger.github.io/tt-live-results/
    output: D:/TimeTrial_Refactor/race_results_qr.png
"""

import sys
from pathlib import Path

import qrcode
from qrcode.image.styledpil import StyledPilImage
from PIL import Image, ImageDraw, ImageFont


DEFAULT_URL = "https://timothy-granger.github.io/tt-live-results/"
DEFAULT_OUTPUT = Path("D:/TimeTrial_Refactor/race_results_qr.png")


def generate_qr(url: str = DEFAULT_URL, output_path: Path = DEFAULT_OUTPUT) -> Path:
    """Generate a QR code with title text, suitable for printing."""

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_w, qr_h = qr_img.size

    # Create final image with title and URL text
    margin = 40
    title_height = 80
    url_height = 50
    total_h = margin + title_height + qr_h + url_height + margin
    total_w = max(qr_w + margin * 2, 500)

    img = Image.new("RGB", (total_w, total_h), "white")
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 32)
        url_font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        title_font = ImageFont.load_default()
        url_font = ImageFont.load_default()

    # Title
    title = "SCAN FOR LIVE RESULTS"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(
        ((total_w - title_w) // 2, margin),
        title, fill="black", font=title_font,
    )

    # QR code centered
    qr_x = (total_w - qr_w) // 2
    qr_y = margin + title_height
    img.paste(qr_img, (qr_x, qr_y))

    # URL below QR
    url_bbox = draw.textbbox((0, 0), url, font=url_font)
    url_w = url_bbox[2] - url_bbox[0]
    draw.text(
        ((total_w - url_w) // 2, qr_y + qr_h + 10),
        url, fill="#444444", font=url_font,
    )

    img.save(str(output_path))
    print(f"QR code saved: {output_path}")
    print(f"URL: {url}")
    print(f"Image size: {total_w}x{total_h} — print at full size for best scanning")

    return output_path


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    generate_qr(url, output)
