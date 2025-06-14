FROM python:3.10-bullseye

RUN apt-get update && \
    apt-get install -y libgl1 libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server ./server

EXPOSE 7860

CMD ["python", "server/server.py", "--host", "0.0.0.0"]
