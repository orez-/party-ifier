"""
Helper script to snapshot the outputs of the partyifier for all possible flags for a given image.

To use, create a folder in the `tests` dir and add a file named `original` with the appropriate
extension. Then run this script with that folder name.

Note that although this script generates all possible permutations of the flags, not all resulting
images are interesting. Feel free to delete uninteresting images.
"""

import itertools
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import PIL.Image

from src import partyifier


def original_filename(path):
    for filename in os.listdir(path):
        full_filename = path/filename
        if full_filename.stem == "original":
            return full_filename
    return None


def main():
    if len(sys.argv) <= 1:
        print("Must pass test name")
        sys.exit(1)
    test_name = sys.argv[1]
    path = pathlib.Path(__file__).parent/test_name
    filename = original_filename(path)
    if not filename:
        print(
            f"Could not find `{test_name}/original` file. Make sure the directory exists, "
            "and contains an image with the proper extension named `original`"
        )
        sys.exit(1)
    image = PIL.Image.open(filename)
    for color, rotate, fit, crop_circular in itertools.product([False, True], repeat=4):
        new_image = partyifier.partyify(
            image,
            color=color,
            rotate=rotate,
            fit=fit,
            crop_circular=crop_circular,
        )
        name = '_'.join(filter(None, [
            color and "color",
            rotate and "rotate",
            fit and "fit",
            crop_circular and "crop",
        ])) or "none"
        with open(path/f"{name}.gif", "wb") as file:
            file.write(new_image.read())



if __name__ == "__main__":
    main()
