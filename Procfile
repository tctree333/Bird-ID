worker: python3 -m bot
web: gunicorn -k uvicorn.workers.UvicornWorker -w 4 web.main:app