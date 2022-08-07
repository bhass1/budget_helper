FROM python:3.10-slim

WORKDIR /usr/src/app

RUN /usr/local/bin/python -m pip install --upgrade pip

COPY requirements.txt ./
RUN pip install --root-user-action=ignore --no-cache-dir -r requirements.txt

COPY main.py ./
COPY test/ ./test/

CMD [ "python", "./main.py"]
