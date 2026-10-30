import io

import pytest
from PIL import Image

from core.image_prep import MAX_IMAGE_BYTES, MAX_SIDE, ImageError, prepare_image


def save(img, fmt, **kw):
    out = io.BytesIO()
    img.save(out, fmt, **kw)
    return out.getvalue()


def test_png_text_metadata_is_removed():
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add_text("Comment", "SECRET-PNG-COMMENT")
    original = save(Image.new("RGB", (50, 40), "white"), "PNG", pnginfo=info)
    assert b"SECRET-PNG-COMMENT" in original

    cleaned, media_type = prepare_image(original)
    assert media_type == "image/png"
    assert b"SECRET-PNG-COMMENT" not in cleaned
    assert Image.open(io.BytesIO(cleaned)).size == (50, 40)


def test_jpeg_exif_is_removed():
    exif = Image.Exif()
    exif[0x010F] = "SECRET-CAMERA-MAKER"
    exif[0x0132] = "2026:10:30 01:00:00"
    original = save(Image.new("RGB", (60, 40), "white"), "JPEG", exif=exif.tobytes())
    assert b"SECRET-CAMERA-MAKER" in original

    cleaned, media_type = prepare_image(original)
    assert media_type == "image/jpeg"
    assert b"SECRET-CAMERA-MAKER" not in cleaned
    assert len(Image.open(io.BytesIO(cleaned)).getexif()) == 0


def test_large_image_is_resized_to_the_limit():
    cleaned, _ = prepare_image(save(Image.new("RGB", (3000, 2000), "white"), "PNG"))
    assert max(Image.open(io.BytesIO(cleaned)).size) == MAX_SIDE


@pytest.mark.parametrize("mode", ["P", "L", "RGBA", "1"])
def test_other_png_modes_are_handled(mode):
    cleaned, media_type = prepare_image(save(Image.new(mode, (20, 20)), "PNG"))
    assert media_type == "image/png" and Image.open(io.BytesIO(cleaned)).size == (20, 20)


@pytest.mark.parametrize("bad", [
    b"", None, "text", b"hello world", b"GIF89a" + b"0" * 50,
    b"\x89PNG\r\n\x1a\n" + b"garbage", b"\xff\xd8\xff" + b"garbage",
])
def test_non_images_and_other_formats_are_rejected(bad):
    with pytest.raises(ImageError):
        prepare_image(bad)


def test_webp_is_rejected_even_if_named_png():
    webp = save(Image.new("RGB", (10, 10)), "WEBP")
    with pytest.raises(ImageError):
        prepare_image(webp)


def test_oversized_file_is_rejected():
    with pytest.raises(ImageError, match="5 MB"):
        prepare_image(b"\x89PNG\r\n\x1a\n" + b"0" * MAX_IMAGE_BYTES)


def test_image_with_too_many_pixels_is_rejected_without_decoding_it():
    huge = save(Image.new("1", (7000, 7000)), "PNG")  # 49 million pixels, tiny file
    assert len(huge) < MAX_IMAGE_BYTES
    with pytest.raises(ImageError, match="too many pixels"):
        prepare_image(huge)
