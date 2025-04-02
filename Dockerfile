FROM python:3.13.2

ENV HOME=/home/fast \
    APP_HOME=/home/fast/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN mkdir -p $APP_HOME \
    && groupadd -r fast \
    && useradd -r -g fast fast \
    && apt install curl

WORKDIR $HOME

COPY ./requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r ./requirements.txt \
    && chown -R fast:fast .


COPY . .

USER fast