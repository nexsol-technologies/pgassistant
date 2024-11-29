
FROM python:3.12.4-alpine3.20

RUN apk update && apk upgrade && apk add postgresql-client && apk add util-linux && apk add bash
RUN python -m pip install --upgrade pip
RUN pip install gunicorn

# Create a pgassistant group and user 
RUN addgroup -S pgassistant && adduser -S pgassistant -G pgassistant -h /home/pgassistant
USER pgassistant

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV DEBUG=False

WORKDIR /home/pgassistant

# Create a virtual env for pgassistant user
RUN python -m venv /home/pgassistant/venv
# activate environment
ENV PATH="/home/pgassistant/venv/bin:$PATH"

COPY --chown=pgassistant:pgassistant requirements.txt /home/pgassistant/requirements.txt 

# install python dependencies 
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /home/pgassistant/requirements.txt

COPY --chown=pgassistant:pgassistant ./env.sample /home/pgassistant/.env
COPY --chown=pgassistant:pgassistant ./apps /home/pgassistant/apps
COPY --chown=pgassistant:pgassistant ./media /home/pgassistant/media
COPY --chown=pgassistant:pgassistant ./gunicorn-cfg.py /home/pgassistant/gunicorn-cfg.py
COPY --chown=pgassistant:pgassistant ./queries.json /home/pgassistant/queries.json
COPY --chown=pgassistant:pgassistant ./render.yaml /home/pgassistant/render.yaml
COPY --chown=pgassistant:pgassistant ./pgtune.sh /home/pgassistant/pgtune.sh 
COPY --chown=pgassistant:pgassistant ./run.py /home/pgassistant/run.py 

EXPOSE 5085

# gunicorn
ENTRYPOINT  ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]
