import os.path

import PIL.Image
import PIL.ImageOps
import StringIO
import flask
import requests

import images2gif


def tint_image(src, color):
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


def party(img_data, rotate, color, fit):
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
    rotations = xrange(0, 360, 45)
    assert len(colors) == len(rotations)

    im = PIL.Image.open(img_data)

    width, height = im.size
    if rotate:
        # Provide enough space to avoid clipping.
        side = int(max(im.width, im.height) * (2 ** 0.5))
        width = height = side
    new_image = PIL.Image.new('RGBA', (width, height), (255, 255, 255, 0))
    new_image.paste(im, ((width - im.width) / 2, ((height - im.height) / 2)), mask=im)

    frames = [new_image] * len(colors)
    if color:
        frames = [tint_image(f, color=c) for f, c in zip(frames, colors)]
    if rotate:
        frames = [f.rotate(-r) for f, r in zip(frames, rotations)]
        if fit:
            # Since we happen to be rotating at 45 degree angles we could
            # get away with only checking the first two bounding boxes,
            # but for the sake of simplicity and completeness (at the
            # cost of performance) we'll check all of them.
            to_crop = min(reapply_transparency(f, (0, 0, 0, 0)).getbbox()[0] for f in frames)

            frames = [
                f.crop((to_crop, to_crop, f.width - to_crop, f.height - to_crop))
                for f in frames
            ]

    frames = [reapply_transparency(f).convert('P') for f in frames]

    gif_data = StringIO.StringIO()
    images2gif.writeGif(
        gif_data,
        frames,
        duration=0.0625,
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


@app.route('/result', methods=['POST'])
def result():
    MAX_LENGTH = 1 * 1000 * 1000

    url = flask.request.form['url']
    color = 'color' in flask.request.form
    rotate = 'rotate' in flask.request.form
    fit = 'fit' in flask.request.form

    img_response = requests.get(url, stream=True)
    content_length = int(img_response.headers['Content-Length'])
    if int(content_length) > MAX_LENGTH:
        return "Too big"

    data = StringIO.StringIO(img_response.raw.read(content_length))

    if not color and not rotate:
        # Why are you even here then.
        mimetype = img_response.headers['Content-Type']
        return flask.send_file(data, mimetype=mimetype)

    gif_data = party(data, color=color, rotate=rotate, fit=fit)
    return flask.send_file(gif_data, mimetype='image/gif')


# if __name__ == '__main__':
#     app.run()
