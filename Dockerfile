FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && apt-get clean

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml /app/

RUN poetry lock

RUN poetry install --no-root --no-dev

COPY . /app/

CMD ["poetry", "run", "python3", "-u", "-m", "src.agent.main"]
