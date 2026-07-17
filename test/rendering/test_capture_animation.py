from io import BytesIO

from PIL import Image, ImageSequence

from rendering.capture_animation import (
    SPRITE_SIZE,
    CaptureAnimation,
    _normalize_sprite_frames,
)


def sprite(size, box, color=(255, 0, 0, 255)):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    from PIL import ImageDraw

    ImageDraw.Draw(image).rectangle(box, fill=color)
    return image


def visible_box(image):
    return image.getchannel("A").getbbox()


def test_normalization_handles_tall_wide_small_and_lateral_sprites():
    frames = _normalize_sprite_frames(
        [
            sprite((100, 500), (20, 0, 80, 499)),
            sprite((500, 100), (0, 20, 499, 80)),
            sprite((20, 20), (2, 2, 10, 10)),
            sprite((100, 100), (0, 20, 99, 80)),
        ],
        SPRITE_SIZE,
    )

    assert all(frame.size == (SPRITE_SIZE, SPRITE_SIZE) for frame in frames)
    assert all(visible_box(frame) for frame in frames)
    assert visible_box(frames[0])[3] == SPRITE_SIZE


def test_normalization_uses_common_scale_and_stable_baseline():
    frames = _normalize_sprite_frames(
        [
            sprite((200, 300), (20, 40, 180, 299)),
            sprite((200, 300), (0, 0, 199, 199)),
        ],
        SPRITE_SIZE,
    )

    assert [frame.size for frame in frames] == [(108, 140), (108, 140)]
    assert [visible_box(frame)[3] for frame in frames] == [140, 140]
    assert [visible_box(frame)[2] - visible_box(frame)[0] for frame in frames] == [
        87,
        108,
    ]


def test_normalization_handles_transparent_frames_and_preserves_alpha():
    transparent = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    frames = _normalize_sprite_frames(
        [transparent, sprite((80, 80), (10, 10, 50, 70))],
        SPRITE_SIZE,
    )

    assert visible_box(frames[0]) is None
    assert frames[0].mode == "RGBA"
    assert frames[1].mode == "RGBA"


def test_gen9_proportions_fit_the_capture_box():
    for width, height in [(366, 536), (390, 495), (470, 573), (468, 569)]:
        frame = _normalize_sprite_frames(
            [sprite((width, height), (0, 0, width - 1, height - 1))],
            SPRITE_SIZE,
        )[0]
        box = visible_box(frame)
        assert box[2] - box[0] <= SPRITE_SIZE
        assert box[3] - box[1] <= SPRITE_SIZE


def test_sprite_frame_advance_preserves_order_and_duration():
    animation = CaptureAnimation.__new__(CaptureAnimation)
    animation.sprite_frames = [object(), object(), object()]
    animation.sprite_durations = [80, 80, 80]
    animation.sprite_index = 0
    animation.sprite_timer = 0

    animation.advance_sprite_frame(80)
    assert animation.sprite_index == 1
    assert animation.sprite_timer == 0

    animation.advance_sprite_frame(80)
    assert animation.sprite_index == 2
    assert animation.sprite_timer == 0


def test_normalized_frames_can_be_saved_as_a_valid_400x225_gif():
    frames = [
        Image.new("RGBA", (400, 225), (0, 0, 0, 0)),
        Image.new("RGBA", (400, 225), (255, 255, 255, 255)),
    ]
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,
    )
    output.seek(0)
    gif = Image.open(output)
    decoded = list(ImageSequence.Iterator(gif))
    assert gif.size == (400, 225)
    assert len(decoded) == 2
    assert [frame.info["duration"] for frame in decoded] == [80, 80]
