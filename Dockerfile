FROM python:3.9

WORKDIR /app

COPY . .

RUN mkdir data
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
