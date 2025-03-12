import base64
import os
import subprocess
import traceback
from pathlib import Path
from aiohttp.web_middlewares import Handler
import pyvips
from aiohttp import web, ClientSession, ClientError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp_tus import setup_tus, constants, validators
import argparse
from aiohttp_tus.data import Resource
import jwt

# --host $HOST --port $PORT --url $URL_LOCATION --callback $UPLOAD_CALLBACK --dir $UPLOAD_DIRECTORY --gen-host $GEN_HOST --gen-scheme $GEN_SCHEME --client-max-size $CLIENT_MAX_SIZE
parser = argparse.ArgumentParser(description='aiohttp implementation of TUS file server')
parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '9000')))
parser.add_argument('--client-max-size', type=int, default=int(os.getenv('CLIENT_MAX_SIZE', f'{110 * 1000 * 1000}')))
parser.add_argument('--preview-size', type=int, default=int(os.getenv('PREVIEW_SIZE', f'512')))
parser.add_argument('--preview-large-size', type=int, default=int(os.getenv('PREVIEW_LARGE_SIZE', f'1920')))
parser.add_argument('--host', type=str, default=os.getenv('HOST', 'localhost'))
parser.add_argument('--url', type=str, default=os.getenv('URL_LOCATION', '/tus/'))
parser.add_argument(
    '--callback', type=str,
    default=os.getenv('UPLOAD_CALLBACK', 'http://localhost:8000/upload/callback/')
)
parser.add_argument(
    '--secret', type=str, default=os.getenv('SECRET_KEY'),
    help='Secret key for JWT, shared with backend'
)
parser.add_argument(
    '--secret-path', type=str, default=os.getenv('SECRET_KEY_PATH'),
    help='Path to the file containing the secret key for JWT, shared with backend'
)
parser.add_argument('--secret-key-algorithm', type=str, default=os.getenv('SECRET_KEY_ALGORITHM', 'HS256'))
parser.add_argument('--dir', type=str, default=os.getenv('UPLOAD_DIRECTORY'))
parser.add_argument('--gen-scheme', type=str, default=os.getenv('GEN_SCHEME'))
parser.add_argument('--gen-host', type=str, default=os.getenv('GEN_HOST'))
parser.add_argument('--include-hash', type=str, default=os.getenv('INCLUDE_HASH', '0'))
args = parser.parse_args()
assert args.secret or args.secret_path, 'SECRET_KEY or SECRET_KEY_PATH is required'
assert args.dir, 'UPLOAD_DIRECTORY is required'
args.dir = Path(args.dir)
args.include_hash = args.include_hash == '1'

if args.secret_path:
    with open(args.secret_path, 'r', encoding='utf-8') as f:
        args.secret = f.read()


def parse_metadata(metadata: str):
    metadata = {v.split(' ')[0]: base64.b64decode(v.split(' ')[1]).decode('utf-8') for v in metadata.split(',')}
    jwt_metadata = jwt.decode(metadata['jwt'], args.secret, algorithms=[args.secret_key_algorithm])
    assert jwt_metadata['filename'] == metadata['filename']
    assert set(metadata.keys()) == {'filename', 'jwt'}
    return jwt_metadata


async def on_upload_done(request: web.Request, resource: Resource, path: Path):
    metadata = parse_metadata(resource.metadata_header)

    path = str(path)
    if 'path' in metadata:
        destination = args.dir / metadata.get('path')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = str(destination)
        os.rename(path, destination)
        path = destination

    has_thumbnail = True
    try:
        if 'preview' in metadata:
            preview = args.dir / metadata.get('preview')
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview = str(preview)
            thumbnail: pyvips.Image = pyvips.Image.thumbnail(path, args.preview_size)
            thumbnail.write_to_file(preview)

        if 'preview-large' in metadata:
            preview_large = args.dir / metadata.get('preview-large')
            preview_large.parent.mkdir(parents=True, exist_ok=True)
            preview_large = str(preview_large)
            thumbnail: pyvips.Image = pyvips.Image.thumbnail(path, args.preview_large_size)
            thumbnail.write_to_file(preview_large)
    except pyvips.Error:
        has_thumbnail = False

    if args.include_hash:
        metadata['hash'] = subprocess.check_output(['cksum', path]).decode('utf-8').split(' ')[0]
    await call_callback(metadata, has_thumbnail)


async def call_callback(metadata, has_thumbnail=True):
    if not args.callback:
        return False
    try:
        async with ClientSession() as session:
            async with session.post(args.callback, data={
                **metadata,
                'has_thumbnail': 'true' if has_thumbnail else 'false'
            }) as resp:
                return resp.status == 200
    except ClientError:
        return False


def request_decorator(handler: Handler):
    async def _handler(request: Request):
        if request.method == 'POST' and constants.HEADER_UPLOAD_METADATA in request.headers:
            try:
                parse_metadata(request.headers[constants.HEADER_UPLOAD_METADATA])
            except (jwt.ExpiredSignatureError, ValueError):
                # If the token has expired, return an error response
                return Response(status=403, text="Token has expired")
            except jwt.InvalidTokenError:
                # If the token is invalid, return an error response
                return Response(status=403, text="Invalid token")

        request = request.clone(
            scheme=request.headers.get('X-Tus-Scheme') or args.gen_scheme or request.scheme,
            host=request.headers.get('X-Tus-Host') or args.gen_host or request.host,
        )

        try:
            return await handler(request)
        except web.HTTPClientError as e:
            traceback.print_exc()
            if request.method == 'HEAD' and constants.HEADER_UPLOAD_METADATA in request.headers:
                await call_callback(parse_metadata(request.headers[constants.HEADER_UPLOAD_METADATA]))
            raise e

    return _handler


app = setup_tus(
    web.Application(
        client_max_size=args.client_max_size,
    ),
    upload_path=args.dir,
    upload_url=args.url,
    on_upload_done=on_upload_done,
    decorator=request_decorator
)

if __name__ == '__main__':
    web.run_app(app, host=args.host, port=args.port)
