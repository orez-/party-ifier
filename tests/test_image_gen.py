import io
import os
import pathlib
import re

import PIL.Image
import pytest

from src import partyifier


def load_test_images(test_name):
    options = "(?:color|rotate|fit|crop)"
    path = pathlib.Path(__file__).parent/test_name
    images = {}
    for filename in os.listdir(path):
        full_filename = path/filename
        stem = full_filename.stem
        if stem == "original":
            key = "original"
        elif stem == "none":
            key = frozenset()
        elif re.fullmatch(rf"{options}(?:_{options})*", stem):
            key = frozenset(stem.split("_"))
            if "crop" in key:
                key ^= {"crop_circular", "crop"}
        else:
            continue
        assert key not in images, f"duplicate file case {test_name}/{stem}"
        with open(full_filename, "rb") as file:
            images[key] = io.BytesIO(file.read())
    assert "original" in images
    return images


def get_test_directories():
    path = pathlib.Path(__file__).parent
    _, test_dirs, _ = next(os.walk(path))
    return test_dirs


@pytest.mark.parametrize("test_name", get_test_directories())
def test_parties(test_name):
    images = load_test_images(test_name)

    original = PIL.Image.open(images.pop("original"))
    fields = dict(color=False, rotate=False, fit=False, crop_circular=False)

    for key, expected in images.items():
        on_fields = {k: True for k in key}
        actual = partyifier.partyify(original, **{**fields, **on_fields})
        assert actual.read() == expected.read()
