FROM python:3.8.5 as builder

WORKDIR /build

COPY . .

RUN pip install poetry

RUN poetry config virtualenvs.create false

RUN poetry install

RUN poetry run pytest

RUN poetry build -f wheel

FROM python:3.8.5-slim-buster

COPY --from=builder /build/dist/engine-0.1.0-py3-none-any.whl .

RUN pip install engine-0.1.0-py3-none-any.whl

ENTRYPOINT ["python", "-m", "engine"]