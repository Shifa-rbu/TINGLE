"""Checks an uploaded screenshot and removes its metadata before it is sent anywhere.

Only PNG and JPEG are accepted (checked by the file's real bytes, not its name).
The image is re-built from raw pixels, which drops EXIF (location, camera, time),
text chunks and colour-profile data. Nothing is written to disk.
"""

import io

from PIL import Image

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB upload limit
MAX_PIXELS = 40_000_000  # refuse huge images before decoding them
MAX_SIDE = 1568  # longest side after resizing (keeps the request small)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


class ImageError(Exception):
    """The message is safe to show to the user."""


def prepare_image(data):
    """Return (clean_bytes, media_type) or raise ImageError."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ImageError("No image data was received.")
    data = bytes(data)
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageError("The image is larger than 5 MB. Please upload a smaller screenshot.")
    if not (data.startswith(PNG_MAGIC) or data.startswith(JPEG_MAGIC)):
        raise ImageError("Only PNG or JPG screenshots are supported.")

    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ("PNG", "JPEG"):
            raise ImageError("Only PNG or JPG screenshots are supported.")
        if img.width * img.height > MAX_PIXELS:
            raise ImageError("The image has too many pixels. Please upload a smaller screenshot.")
        img.load()  # decode (first frame only)
    except ImageError:
        raise
    except Exception:
        raise ImageError("The file could not be read as a valid image.") from None

    original_format = img.format
    if img.mode not in ("RGB", "RGBA", "L"):
        has_alpha = "A" in img.mode or "transparency" in img.info
        img = img.convert("RGBA" if has_alpha and original_format == "PNG" else "RGB")

    img.thumbnail((MAX_SIDE, MAX_SIDE))

    # Rebuild from raw pixels so no metadata can be carried over.
    clean = Image.frombytes(img.mode, img.size, img.tobytes())
    out = io.BytesIO()
    if original_format == "PNG":
        clean.save(out, "PNG")
        return out.getvalue(), "image/png"
    clean.save(out, "JPEG", quality=90)
    return out.getvalue(), "image/jpeg"
