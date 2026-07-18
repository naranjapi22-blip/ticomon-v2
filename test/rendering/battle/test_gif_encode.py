from PIL import Image

from rendering.battle.layout import DISCORD_MAX_GIF_BYTES
from rendering.battle.gif_encode import encode_battle_gif, subsample_frame_indices


def test_subsample_frame_indices_evenly_distributes_frames():
    assert subsample_frame_indices(80, 20) == [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76]
    assert subsample_frame_indices(3, 20) == [0, 1, 2]


def test_encode_battle_gif_stays_under_discord_limit_for_many_frames():
    frames = [
        Image.new("RGB", (1020, 574), (index % 255, 40, 120))
        for index in range(80)
    ]
    durations = [100] * len(frames)

    encoded = encode_battle_gif(frames, durations)

    assert encoded.startswith(b"GIF")
    assert len(encoded) <= DISCORD_MAX_GIF_BYTES
