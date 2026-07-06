import pytest

from core.creature.size import Size


def test_valid_size():
    size = Size(1.0)

    assert size.value == 1.0


@pytest.mark.parametrize("value", [0.49, 1.51])
def test_invalid_size(value):
    with pytest.raises(ValueError):
        Size(value)
