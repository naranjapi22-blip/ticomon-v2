from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from scripts.normalize_gifs import normalize_frames


def frame(size, box, color=(255, 0, 0, 255)):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle(box, fill=color)
    return image


def test_normalizes_large_canvas_and_preserves_proportion():
    result = normalize_frames([frame((470, 573), (0, 0, 429, 568))])
    visible = result[0].getchannel("A").getbbox()

    assert result[0].size == (240, 240)
    assert visible[2] - visible[0] <= 220
    assert visible[3] - visible[1] <= 220
    assert (visible[2] - visible[0]) / (visible[3] - visible[1]) == pytest.approx(
        430 / 569,
        rel=0.02,
    )


def test_common_scale_and_fixed_baseline_for_variable_frames():
    result = normalize_frames(
        [
            frame((300, 300), (20, 20, 279, 279)),
            frame((300, 300), (0, 80, 299, 239)),
            Image.new("RGBA", (300, 300), (0, 0, 0, 0)),
        ]
    )
    boxes = [image.getchannel("A").getbbox() for image in result]

    assert all(image.size == (240, 240) for image in result)
    assert boxes[0][3] == boxes[1][3] == 230
    assert boxes[2] is None
    assert result[0].mode == "RGBA"


def test_gif_durations_loop_and_frame_order_survive_round_trip():
    source = BytesIO()
    frames = normalize_frames(
        [
            frame((400, 200), (0, 50, 199, 149), (255, 0, 0, 255)),
            frame((400, 200), (200, 50, 399, 149), (0, 255, 0, 255)),
        ]
    )
    frames[0].save(
        source,
        format="GIF",
        save_all=True,
        append_images=[frames[1]],
        duration=[100, 200],
        loop=3,
        disposal=2,
        optimize=False,
    )
    source.seek(0)
    with Image.open(source) as output:
        decoded = []
        durations = []
        for index in range(output.n_frames):
            output.seek(index)
            decoded.append(output.convert("RGBA"))
            durations.append(output.info["duration"])
        assert output.size == (240, 240)
        assert output.info["loop"] == 3
        assert durations == [100, 200]
        assert len(decoded) == 2
        assert decoded[0].getchannel("A").getbbox() is not None
        assert decoded[1].getchannel("A").getbbox() is not None
        assert max(decoded[0].getchannel("R").getdata()) > 0
        assert max(decoded[1].getchannel("G").getdata()) > 0
