FROM python:3.10-bullseye

WORKDIR /app

COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server ./server

EXPOSE 7860

CMD ["python", "server/server.py"]
