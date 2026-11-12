import pytest
from PIL import Image

from paint_tes.document import Document
from paint_tes.imageops import (
    composite_edit,
    expand_canvas,
    padded_for_engine,
    selection_mask,
    validate_size,
)


def test_inpaint_preserves_every_unselected_pixel():
    source = Image.new("RGBA", (64, 64), (17, 29, 45, 99))
    generated = Image.new("RGBA", source.size, "red")
    mask = selection_mask(source.size, rectangle=(10, 10, 20, 20))
    result = composite_edit(source, generated, mask)
    assert result.getpixel((0, 0)) == source.getpixel((0, 0))
    assert result.getpixel((15, 15)) == generated.getpixel((15, 15))
    for x in range(64):
        for y in range(64):
            if not mask.getpixel((x, y)):
                assert result.getpixel((x, y)) == source.getpixel((x, y))


def test_outpaint_mask_and_original_alpha():
    source = Image.new("RGBA", (32, 32), (10, 20, 30, 128))
    expanded, mask = expand_canvas(source, 16, 32, 48, 64)
    assert expanded.size == (96, 128)
    assert mask.getpixel((16, 32)) == 0
    assert mask.getpixel((0, 0)) == 255
    result = composite_edit(expanded, Image.new("RGBA", expanded.size, "green"), mask)
    assert result.crop((16, 32, 48, 64)).tobytes() == source.tobytes()


def test_padding_does_not_resample_source_or_selection():
    source = Image.new("RGBA", (33, 43), "red")
    source.putpixel((32, 42), (1, 2, 3, 4))
    mask = Image.new("L", source.size, 255)
    padded, pmask = padded_for_engine(source, mask)
    assert padded.size == (48, 48)
    assert padded.crop((0, 0, 33, 43)).tobytes() == source.tobytes()
    assert pmask.getpixel((47, 47)) == 0


def test_size_and_mask_validation():
    with pytest.raises(ValueError):
        validate_size(8192, 8192)
    with pytest.raises(ValueError):
        expand_canvas(Image.new("RGBA", (32, 32)), -1, 0, 0, 0)
    with pytest.raises(ValueError):
        composite_edit(
            Image.new("RGBA", (32, 32)), Image.new("RGBA", (64, 64)), Image.new("L", (32, 32))
        )


def test_lasso_closes_and_rectangle_reverses():
    mask = selection_mask((64, 64), points=[(10, 10), (50, 10), (30, 50)])
    assert mask.getpixel((30, 20)) == 255
    assert mask.getpixel((0, 0)) == 0
    assert selection_mask((64, 64), rectangle=(40, 40, 10, 10)).getbbox() == (10, 10, 41, 41)


def test_history_saved_revision_and_branching():
    doc = Document(Image.new("RGBA", (32, 32), "red"))
    doc.saved_revision = 0
    doc.apply(Image.new("RGBA", (32, 32), "green"))
    doc.saved_revision = doc.revision
    doc.apply(Image.new("RGBA", (32, 32), "blue"))
    doc.undo()
    assert not doc.dirty
    doc.undo()
    assert doc.dirty
    doc.apply(Image.new("RGBA", (32, 32), "yellow"))
    assert doc.dirty
    assert not doc.redo_history
    doc.undo()
    doc.redo()
    assert doc.image.getpixel((0, 0)) == (255, 255, 0, 255)
