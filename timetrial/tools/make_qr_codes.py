"""Generate labeled QR-code images for the 2026 club Time Trial series.

For each race this writes three PNGs to ``registration/qr/``:

  * ``qr_race{N}_register.png`` — registration-form QR with caption
  * ``qr_race{N}_entries.png``  — public entry-list QR with caption
  * ``qr_sheet_race{N}.png``    — printable sheet with BOTH QR codes side by
                                  side under the series title

Run:
    .venv/Scripts/python.exe -m timetrial.tools.make_qr_codes

To refresh for a new season, edit ``RACES`` below (and the title strings if the
sponsor changes) and re-run. URLs are the same ones tracked in
``registration/links.cheat.sheet.txt``.
"""

from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

# --- Branding --------------------------------------------------------------
SERIES_TITLE = "Greenville Spinners Time Trial"
SERIES_SUBTITLE = "Presented by Velo Valets"

NAVY = (27, 42, 74)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

# --- Race data (Races 2-4; Race 1 / May 28 already ran) --------------------
RACES = [
    {
        "number": 2,
        "date": "June 25, 2026",
        "register": "https://forms.gle/P9i5M464uLG7xLdo8",
        "entries": "https://docs.google.com/spreadsheets/d/e/2PACX-1vR0pW4faIWZknd9ANExylxBAaJl6seA5ay1CVJCCUtYUvGvEoclcLqvA7K0y6ZC5Pnmy9mn38hVbA92/pubhtml?gid=637823728&single=true",
    },
    {
        "number": 3,
        "date": "July 30, 2026",
        "register": "https://forms.gle/kRVJQBdKyGn14e67A",
        "entries": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRHW1J_seR3wFwFUXOBwNSJ6af1K2B1l2lS6r4Rt4rdCuUwt0p2qUdIdFZn185AcfFD9eAQ2J0fNCRI/pubhtml?gid=457774554&single=true",
    },
    {
        "number": 4,
        "date": "August 27, 2026",
        "register": "https://forms.gle/urs5pef4hDLp55wF7",
        "entries": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSzzpNO6YWRbPR0vQh8SW29bESBnugxzR2B9ZfGWhbdqr3YatdTgW1oxCd1RseNnTvKH5olLZcAC5UG/pubhtml?gid=886836395&single=true",
    },
]

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "registration" / "qr"

_SCRATCH = ImageDraw.Draw(Image.new("RGB", (4, 4)))


# --- Helpers ---------------------------------------------------------------
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    left, _, right, _ = _SCRATCH.textbbox((0, 0), text, font=font)
    return right - left


def _qr_image(url: str, box_size: int = 10, border: int = 2) -> Image.Image:
    """Render ``url`` as a black-on-white QR code (medium error correction)."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.get_image().convert("RGB")


def make_labeled_qr(url: str, race_line: str, action: str, out_path: Path) -> Path:
    """One QR code with the club name + race line above and an action below."""
    qr = _qr_image(url, box_size=10, border=2)
    qw, qh = qr.size

    club_font = _font(FONT_BOLD, 30)
    race_font = _font(FONT_REGULAR, 26)
    action_font = _font(FONT_BOLD, 34)

    pad, gap = 36, 14
    club_h = _line_height(club_font)
    race_h = _line_height(race_font)
    action_h = _line_height(action_font)

    content_w = max(
        qw,
        _text_width(SERIES_TITLE, club_font),
        _text_width(race_line, race_font),
        _text_width(action, action_font),
    )
    width = content_w + pad * 2
    height = pad + club_h + gap + race_h + gap + qh + gap + action_h + pad

    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    cx = width // 2

    y = pad
    draw.text((cx, y), SERIES_TITLE, font=club_font, fill=NAVY, anchor="ma")
    y += club_h + gap
    draw.text((cx, y), race_line, font=race_font, fill=BLACK, anchor="ma")
    y += race_h + gap
    img.paste(qr, ((width - qw) // 2, y))
    y += qh + gap
    draw.text((cx, y), action, font=action_font, fill=NAVY, anchor="ma")

    img.save(out_path)
    return out_path


def make_race_sheet(race: dict, out_path: Path, qsize: int = 380) -> Path:
    """Printable sheet: both QR codes side by side under the series title."""
    reg_qr = _qr_image(race["register"]).resize(
        (qsize, qsize), Image.Resampling.NEAREST
    )
    ent_qr = _qr_image(race["entries"]).resize(
        (qsize, qsize), Image.Resampling.NEAREST
    )

    width = 1000
    pad, gap = 50, 18

    title_font = _font(FONT_BOLD, 52)
    sub_font = _font(FONT_REGULAR, 30)
    race_font = _font(FONT_BOLD, 38)
    cap_font = _font(FONT_BOLD, 30)

    th = _line_height(title_font)
    sh = _line_height(sub_font)
    rh = _line_height(race_font)
    ch = _line_height(cap_font)

    qr_y = pad + th + gap + sh + gap + rh + gap * 2
    cap_y = qr_y + qsize + gap
    height = cap_y + ch + pad

    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(12, 12), (width - 12, height - 12)], outline=NAVY, width=4)

    cx = width // 2
    y = pad
    draw.text((cx, y), SERIES_TITLE, font=title_font, fill=NAVY, anchor="ma")
    y += th + gap
    draw.text((cx, y), SERIES_SUBTITLE, font=sub_font, fill=BLACK, anchor="ma")
    y += sh + gap
    draw.text(
        (cx, y),
        f"Race {race['number']} — {race['date']}",
        font=race_font,
        fill=BLACK,
        anchor="ma",
    )

    left_x = 110
    right_x = width - 110 - qsize
    img.paste(reg_qr, (left_x, qr_y))
    img.paste(ent_qr, (right_x, qr_y))
    draw.text(
        (left_x + qsize // 2, cap_y), "Scan to Register",
        font=cap_font, fill=NAVY, anchor="ma",
    )
    draw.text(
        (right_x + qsize // 2, cap_y), "See Who's Registered",
        font=cap_font, fill=NAVY, anchor="ma",
    )

    img.save(out_path)
    return out_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for race in RACES:
        n = race["number"]
        race_line = f"Race {n} — {race['date']}"
        p_reg = make_labeled_qr(
            race["register"], race_line, "Scan to Register",
            OUTPUT_DIR / f"qr_race{n}_register.png",
        )
        p_ent = make_labeled_qr(
            race["entries"], race_line, "See Who's Registered",
            OUTPUT_DIR / f"qr_race{n}_entries.png",
        )
        p_sheet = make_race_sheet(race, OUTPUT_DIR / f"qr_sheet_race{n}.png")
        for p, url in ((p_reg, race["register"]), (p_ent, race["entries"])):
            print(f"wrote {p.name}  <- {url}")
        print(f"wrote {p_sheet.name}  (combined sheet)")


if __name__ == "__main__":
    main()
