FROM python:3.12

ADD AlpacaBot.py .

ADD finbert_utils.py .

COPY requirements.txt .

RUN pip3 install -r requirements.txt

CMD ["python3", "./AlpacaBot.py"]