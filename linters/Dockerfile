FROM python:3.10.2-slim-bullseye

RUN apk add git gcc g++

RUN python -m pip install pre-commit

COPY .pre-commit-config.yaml /src/.pre-commit-config.yaml

WORKDIR /src

CMD ["pre-commit", "run", "--all-files"]
