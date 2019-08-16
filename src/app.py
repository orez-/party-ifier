import contextlib
import io

import flask
import PIL.Image
import requests

from . import partyifier


app = flask.Flask(__name__, static_folder='../static')


@app.route('/', methods=['GET'])
def hello():
    return app.send_static_file('index.html')


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
    crop_circular = 'crop_circular' in flask.request.form

    try:
        with contextlib.closing(requests.get(url, stream=True)) as img_response:
            data = stream_image(img_response)
            data.seek(0)
            if not color and not rotate:
                # Why are you even here then.
                mimetype = img_response.headers['Content-Type']
                return flask.send_file(data, mimetype=mimetype)
    except TooBig:
        return "Too big"

    im = PIL.Image.open(data)
    gif_data = partyifier.partyify(
        im,
        color=color,
        rotate=rotate,
        fit=fit,
        crop_circular=crop_circular,
    )
    return flask.send_file(gif_data, mimetype='image/gif')
