"""Image operations shared by the editor and engine, independent of Qt/CUDA."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .i18n import tr

MAX_SIDE = 8192
MAX_PIXELS = 32 * 1024 * 1024


def validate_size(width: int, height: int) -> None:
    if not (16 <= width <= MAX_SIDE and 16 <= height <= MAX_SIDE) or width * height > MAX_PIXELS:
        raise ValueError(tr("Rozmiar: 16–8192 px na bok, maksymalnie 32 megapiksele."))


def load_image(path) -> Image.Image:
    with Image.open(path) as image:
        validate_size(*image.size)
        return ImageOps.exif_transpose(image).convert("RGBA")


def selection_mask(size, points=None, rectangle=None, feather=0) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if rectangle is not None:
        x0, y0, x1, y1 = rectangle
        draw.rectangle((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), fill=255)
    elif points and len(points) >= 3:
        draw.polygon(points, fill=255)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask


def composite_edit(original: Image.Image, generated: Image.Image, mask: Image.Image) -> Image.Image:
    if original.size != generated.size or mask.size != original.size:
        raise ValueError(tr("Obraz, wynik i maska muszą mieć ten sam rozmiar."))
    return Image.composite(generated.convert("RGBA"), original.convert("RGBA"), mask.convert("L"))


def expand_canvas(image: Image.Image, left: int, top: int, right: int, bottom: int):
    if min(left, top, right, bottom) < 0:
        raise ValueError(tr("Marginesy nie mogą być ujemne."))
    size = (image.width + left + right, image.height + top + bottom)
    validate_size(*size)
    expanded = Image.new("RGBA", size, (255, 255, 255, 0))
    expanded.paste(image, (left, top))
    mask = Image.new("L", size, 255)
    mask.paste(0, (left, top, left + image.width, top + image.height))
    return expanded, mask


def paint_mask(image: Image.Image, mask: Image.Image, color=(255, 255, 255, 0)) -> Image.Image:
    return Image.composite(Image.new("RGBA", image.size, color), image.convert("RGBA"), mask)


def padded_for_engine(image: Image.Image, mask: Image.Image | None, multiple=16):
    """Pad right/bottom without scaling; crop the generated result afterwards."""
    width = (image.width + multiple - 1) // multiple * multiple
    height = (image.height + multiple - 1) // multiple * multiple
    padded = Image.new("RGBA", (width, height), "white")
    padded.paste(image, (0, 0))
    padded_mask = None
    if mask is not None:
        padded_mask = Image.new("L", (width, height), 0)
        padded_mask.paste(mask, (0, 0))
    return padded, padded_mask
