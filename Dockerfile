FROM python:3.11 as base
WORKDIR /app

ENV MENU_ID=15341
ENV LOCATION_ID=56015001
ENV WHERE_AM_I=https://uah.sodexomyway.com/dining-near-me/charger-cafe

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN poetry install --no-root
CMD ["poetry", "run", "/app/main.py"]
