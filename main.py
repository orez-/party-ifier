import contextlib
import io
import itertools
import math
import os.path

import PIL.Image
import PIL.ImageOps
import flask
import requests

import gifextract
import images2gif

import util


PARTY_SPEED = 60
MIN_FRAMES = 8
MIN_DURATION = 20
colors = [
    (252, 88, 91),
    (252, 94, 245),
    (251, 125, 251),
    (204, 125, 250),
    (123, 168, 250),
    (125, 252, 250),
    (125, 251, 126),
    (252, 205, 127),
]


def tint_image(src, color):
    # Only tints 4-band images.
    color = '#{:x}{:x}{:x}'.format(*color)
    r, g, b, alpha = src.split()
    gray = PIL.ImageOps.grayscale(src)
    result = PIL.ImageOps.colorize(gray, (0, 0, 0, 0), color)
    result.putalpha(alpha)
    return result


def reapply_transparency(im, alpha_color=(255, 255, 255, 0)):
    new_image = PIL.Image.new('RGBA', im.size, alpha_color)
    new_image.paste(im, (0, 0), mask=im)
    return new_image


def party_img(im, color_id, rotate):
    width, height = im.size
    if rotate is not False:
        # Provide enough space to avoid clipping.
        side = int(max(im.width, im.height) * (2 ** 0.5))
        width = height = side
    new_image = PIL.Image.new('RGBA', (width, height), (255, 255, 255, 0))
    mask = im if im.mode == 'RGBA' else None
    new_image.paste(im, ((width - im.width) // 2, ((height - im.height) // 2)), mask=mask)
    im = new_image

    if color_id is not False:
        im = tint_image(im, color=colors[color_id])
    if rotate is not False:
        im = im.rotate(-rotate)
    return im


def crop_transparency(frames):
    bboxes = [reapply_transparency(frame, (0, 0, 0, 0)).getbbox() for frame in frames]
    crop_box = (
        min(box[0] for box in bboxes),
        min(box[1] for box in bboxes),
        max(box[2] for box in bboxes),
        max(box[3] for box in bboxes),
    )
    return [frame.crop(crop_box) for frame in frames]


def party_static(im, rotate, color, fit):
    width, height = im.size
    new_image = PIL.Image.new('RGBA', im.size, (255, 255, 255, 0))
    mask = im if im.mode == 'RGBA' else None
    new_image.paste(im, ((width - im.width) // 2, ((height - im.height) // 2)), mask=mask)

    frames = [new_image] * len(colors)
    frames = [
        party_img(
            frame,
            color_id=color and i,
            rotate=rotate and (i * 45),
        )
        for i, frame in enumerate(frames)
    ]
    if fit:
        frames = crop_transparency(frames)
    return get_gif(frames)


def adjust_low_durations(frames):
    """
    Low-duration frames tend to be assigned a higher default duration in
    gif viewers, so to compensate we either increase the duration or
    omit the frame entirely.
    """
    for frame, i, duration in frames:
        if duration < MIN_DURATION:
            if duration < MIN_DURATION / 2:
                continue
            duration = MIN_DURATION
        yield frame, i, duration


def party_animated(frames, rotate, color, fit):
    frames = list(frames)
    total_duration = sum(dur for _, dur in frames)
    # cycle to get all the colors at least once
    num_cycles = math.ceil(len(colors) * PARTY_SPEED / total_duration)
    frames = util.ncycles(frames, num_cycles)
    unique_frames = util.zip_duration(
        (frames, lambda fr_dr: fr_dr[1]),
        (itertools.cycle(range(8)), lambda _: PARTY_SPEED),
    )
    unique_frames = (
        (frame, i, duration)
        for ((frame, _), i), duration in unique_frames
    )
    unique_frames = adjust_low_durations(unique_frames)
    frames, durations = zip(*(
        (
            party_img(
                frame,
                color_id=color and i % 8,
                rotate=rotate and (i * 45),
            ),
            duration / 1000
        )
        for frame, i, duration in unique_frames
    ))
    if fit:
        frames = crop_transparency(frames)
    return get_gif(frames, durations)


def get_gif(frames, duration=0.0625):
    """
    Convert a set of frames into a gif.
    """
    gif_data = io.BytesIO()
    images2gif.writeGif(
        gif_data,
        frames,
        duration=duration,
        dither=0,
    )
    gif_data.seek(0)
    return gif_data


app = flask.Flask(__name__)
app.debug = True


@app.route('/', methods=['GET'])
def hello():
    default_pic = 'https://s3.amazonaws.com/uploads.hipchat.com/22794/645828/YT5so07G5nkokve/pancake-1434994127%402x.png'
    return '''
        <html>
          <body>
            <form action='result' method='post'>
              <h3>Party-ifier!</h3>
              <input name='url' style='width: 500px' type='text' value='{default_pic}'><br>
              <label><input name='color' type='checkbox' checked> Color</label><br>
              <label><input name='rotate' type='checkbox' checked> Rotate</label><br>
              <label><input name='fit' type='checkbox' checked> Smart Fit</label><br>
              <input type='submit'>
            </form>
          </body>
        </html>
    '''.format(default_pic=default_pic)


class TooBig(ValueError):
    ...


def stream_image(img_response):
    MAX_LENGTH = 1 * 1000 * 1000
    CHUNK_READ_SIZE = 1024  # arbitrary afaict

    data = io.BytesIO()
    content_length = img_response.headers.get('Content-Length')
    if content_length and int(content_length) > MAX_LENGTH:
        raise TooBig("Too big")

    size = 0
    for chunk in img_response.iter_content(CHUNK_READ_SIZE):
        size += len(chunk)
        if size > MAX_LENGTH:
            raise TooBig("Too big")

        data.write(chunk)
    return data


@app.route('/result', methods=['POST'])
def result():
    url = flask.request.form['url']
    color = 'color' in flask.request.form
    rotate = 'rotate' in flask.request.form
    fit = 'fit' in flask.request.form

    try:
        with contextlib.closing(requests.get(url, stream=True)) as img_response:
            data = stream_image(img_response)
            if not color and not rotate:
                # Why are you even here then.
                mimetype = img_response.headers['Content-Type']
                return flask.send_file(data, mimetype=mimetype)
    except TooBig:
        return "Too big"

    im = PIL.Image.open(data)
    # XXX: PIL's `is_animated` on gifs is broken as hell. Seeking past
    # the first frame then seeking back mangles those frames.
    if getattr(im, 'is_animated', False):
        frames = gifextract.processImage(im)
        gif_data = party_animated(frames, color=color, rotate=rotate, fit=fit)
    else:
        gif_data = party_static(im, color=color, rotate=rotate, fit=fit)
    return flask.send_file(gif_data, mimetype='image/gif')


# if __name__ == '__main__':
#     app.run()
