import base64
import os
import traceback
from pathlib import Path
from aiohttp.web_middlewares import _Handler as Handler
import pyvips
from aiohttp import web, ClientSession, ClientError
from aiohttp.web_request import Request
from aiohttp_tus import setup_tus, constants
import argparse
from aiohttp_tus.data import Resource

parser = argparse.ArgumentParser(description='aiohttp implementation of TUS file server')
parser.add_argument('--port', type=int, default=9000)
parser.add_argument('--client-max-size', type=int, default=110 * 1000 * 1000)
parser.add_argument('--host', type=str, default='localhost')
parser.add_argument('--url', type=str, default='/upload/')
parser.add_argument('--callback', type=str, default='http://localhost:8000/uploaded/')
parser.add_argument('--dir', type=str, required=True)
parser.add_argument('--gen-scheme', type=str)
parser.add_argument('--gen-host', type=str)
args = parser.parse_args()
args.dir = Path(args.dir)


def parse_metadata(metadata: str):
    return {v.split(' ')[0]: base64.b64decode(v.split(' ')[1]).decode('utf-8') for v in metadata.split(',')}


async def on_upload_done(request: web.Request, resource: Resource, path: Path):
    metadata = parse_metadata(resource.metadata_header)

    path = str(path)
    if 'path' in metadata:
        destination = args.dir / metadata.get('path')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = str(destination)
        os.rename(path, destination)
        path = destination

    try:
        if 'preview' in metadata:
            preview = args.dir / metadata.get('preview')
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview = str(preview)
            thumbnail: pyvips.Image = pyvips.Image.thumbnail(path, 255)
            thumbnail.write_to_file(preview)

        if 'preview-large' in metadata:
            preview_large = args.dir / metadata.get('preview-large')
            preview_large.parent.mkdir(parents=True, exist_ok=True)
            preview_large = str(preview_large)
            thumbnail: pyvips.Image = pyvips.Image.thumbnail(path, 1920)
            thumbnail.write_to_file(preview_large)
    except pyvips.Error:
        pass

    await call_callback(metadata)


async def call_callback(metadata):
    if not args.callback:
        return False
    try:
        async with ClientSession() as session:
            async with session.post(args.callback, data=metadata) as resp:
                return resp.status == 200
    except ClientError:
        return False


def replace_url(handler: Handler):
    def _handler(request: Request):
        request = request.clone(
            scheme=args.gen_scheme or request.scheme,
            host=args.gen_host or request.host,
        )

        try:
            return handler(request)
        except web.HTTPClientError as e:
            traceback.print_exc()
            if request.method == 'HEAD' and constants.HEADER_UPLOAD_METADATA in request.headers:
                call_callback(parse_metadata(request.headers[constants.HEADER_UPLOAD_METADATA]))
            raise e

    return _handler


app = setup_tus(
    web.Application(
        client_max_size=args.client_max_size,
    ),
    upload_path=args.dir,
    upload_url=args.url,
    on_upload_done=on_upload_done,
    decorator=replace_url
)

if __name__ == '__main__':
    web.run_app(app, host=args.host, port=args.port)
