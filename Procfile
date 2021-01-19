worker: python3 -m bot
web: gunicorn -k uvicorn.workers.UvicornWorker -w 3 web.main:app