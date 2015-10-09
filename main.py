import os.path

import PIL.Image
import PIL.ImageOps
import StringIO
import flask
import requests

import images2gif


filename = 'TEMP_FILE.gif'


def tint_image(src, color):
    color = '#{:x}{:x}{:x}'.format(*color)
    r, g, b, alpha = src.split()
    gray = PIL.ImageOps.grayscale(src)
    result = PIL.ImageOps.colorize(gray, (0, 0, 0, 0), color)
    result.putalpha(alpha)
    return result


def reapply_transparency(im):
    side = im.width
    new_image = PIL.Image.new('RGBA', (side, side), (255, 255, 255, 0))
    new_image.paste(im, (0, 0), mask=im)
    return new_image


def party(img_data):
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

    im = PIL.Image.open(img_data)

    # Provide enough space to avoid clipping.
    side = int(max(im.width, im.height) * (2 ** 0.5))
    new_image = PIL.Image.new('RGBA', (side, side), (255, 255, 255, 0))
    new_image.paste(im, ((side - im.width) / 2, ((side - im.height) / 2)), mask=im)

    frames = [
        reapply_transparency(tint_image(new_image.rotate(-r), color=c)).convert('P')
        for c, r in zip(colors, xrange(0, 360, 45))
    ]

    images2gif.writeGif(
        os.path.join('dest', filename),
        frames,
        duration=0.0625,
        dither=0,
    )


app = flask.Flask(__name__)
app.debug = True

@app.route('/', methods=['GET'])
def hello():
    return '''
        <html>
          <body>
            <form action='result' method='post'>
              <input name='url' type='text' value='https://s3.amazonaws.com/uploads.hipchat.com/22794/645828/YT5so07G5nkokve/pancake-1434994127%402x.png'>
            </form>
          </body>
        </html>
    '''

@app.route('/result', methods=['POST'])
def result():
    MAX_LENGTH = 1 * 1000 * 1000
    url = flask.request.form['url']

    img_response = requests.get(url, stream=True)
    content_length = int(img_response.headers['Content-Length'])
    if int(content_length) > MAX_LENGTH:
        return "Too big"
    data = StringIO.StringIO(img_response.raw.read(content_length))

    party(data)
    return flask.send_from_directory('dest', filename)


if __name__ == '__main__':
    app.run()
