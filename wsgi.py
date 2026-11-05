"""배포 진입점. Vercel은 이 파일의 app을 자동으로 찾음 (vercel.json) · gunicorn은 gunicorn -c gunicorn.conf.py wsgi:app"""
from server import create_app

app = create_app()
