FROM python:3.9.2 as builder

WORKDIR /build

COPY . .

RUN pip install poetry

RUN poetry config virtualenvs.create false

RUN poetry install

RUN poetry run pytest

RUN poetry build -f wheel

FROM python:3.9.2-slim-buster

COPY --from=builder /build/dist/santaka-0.1.0-py3-none-any.whl .

RUN pip install santaka-0.1.0-py3-none-any.whl

ENTRYPOINT ["python", "-m", "santaka.task"]