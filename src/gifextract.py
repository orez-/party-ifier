import contextlib

from PIL import Image


"""
https://gist.github.com/BigglesZX/4016539

I searched high and low for solutions to the "extract animated GIF frames in Python"
problem, and after much trial and error came up with the following solution based
on several partial examples around the web (mostly Stack Overflow).
There are two pitfalls that aren't often mentioned when dealing with animated GIFs -
firstly that some files feature per-frame local palettes while some have one global
palette for all frames, and secondly that some GIFs replace the entire image with
each new frame ('full' mode in the code below), and some only update a specific
region ('partial').
This code deals with both those cases by examining the palette and redraw
instructions of each frame. In the latter case this requires a preliminary (usually
partial) iteration of the frames before processing, since the redraw mode needs to
be consistently applied across all frames. I found a couple of examples of
partial-mode GIFs containing the occasional full-frame redraw, which would result
in bad renders of those frames if the mode assessment was only done on a
single-frame basis.
Nov 2012
"""

DURATION_BUMP = 100
MIN_DURATION = 20

def processImage(im):
    """
    Iterate the GIF, extracting each frame.
    """
    p = im.getpalette()
    last_frame = None

    im.seek(0)
    with contextlib.suppress(EOFError):
        while True:
            # If the GIF uses local colour tables, each frame will have its own palette.
            # If not, we need to apply the global palette to the new frame.
            if not im.getpalette():
                im.putpalette(p)

            new_frame = Image.new('RGBA', im.size)

            # Is this file a "partial"-mode GIF where frames update
            # a region of a different size to the entire image?
            # If so, we need to construct the new frame by pasting it
            # on top of the preceding frames.
            if im.disposal_method != 2 and last_frame:
                new_frame.paste(last_frame)

            position = (0, 0)
            new_frame.paste(im.convert('RGB'), position, im.convert('RGBA'))

            duration = im.info['duration']
            if duration < MIN_DURATION:
                duration = DURATION_BUMP
            yield new_frame, duration

            last_frame = new_frame
            im.seek(im.tell() + 1)
