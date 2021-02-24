FROM python:3.9.2-slim-buster

RUN apt update && apt install -y git

RUN python -m pip install pre-commit

COPY .pre-commit-config.yaml /src/.pre-commit-config.yaml
WORKDIR /src

CMD ["pre-commit", "run", "--all-files"]
