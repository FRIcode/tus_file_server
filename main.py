from pathlib import Path
from aiohttp import web, ClientSession
from aiohttp_tus import setup_tus
import argparse

from aiohttp_tus.data import Resource

parser = argparse.ArgumentParser(description='aiohttp implementation of TUS file server')
parser.add_argument('--port', type=int, default=9000)
parser.add_argument('--host', type=str, default='localhost')
parser.add_argument('--url', type=str, default='/upload/')
parser.add_argument('--callback', type=str, default='http://localhost:8000/uploaded/')
parser.add_argument('--dir', type=str, required=True)
args = parser.parse_args()


async def on_upload_done(request: web.Request, resource: Resource, path: Path):
    if not args.callback:
        return
    async with ClientSession() as session:
        callback_data = {
            'filename': resource.file_name,
            'size': resource.file_size,
            'path': str(path),
            'id': request.headers.get('id'),
        }
        async with session.post(args.callback, data=callback_data) as resp:
            pass


app = setup_tus(
    web.Application(),
    upload_path=Path(args.dir),
    upload_url=args.url,
    on_upload_done=on_upload_done
)

if __name__ == '__main__':
    web.run_app(app, host=args.host, port=args.port)
