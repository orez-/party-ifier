import os.path

import PIL.Image

import images2gif


filename = 'coffee'
with open(os.path.join('src', filename + '.png'), 'rb') as read_file:
    im = PIL.Image.open(read_file)

    # Provide enough space to avoid clipping.
    side = int(max(im.width, im.height) * (2 ** 0.5))
    new_image = PIL.Image.new('RGBA', (side, side), (255, 255, 255, 0))
    new_image.paste(im, ((side - im.width) / 2, ((side - im.height) / 2)), mask=im)
    new_image = new_image.convert('P')

    frames = [new_image.rotate(-r).convert('P') for r in xrange(0, 360, 45)]

    images2gif.writeGif(
        os.path.join('dest', filename + '.gif'),
        frames,
        duration=0.0625,
        dither=0,
    )
