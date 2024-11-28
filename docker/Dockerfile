FROM python:3.10

WORKDIR /code
COPY docker/requirements.txt .

RUN set -eux \
    && pip install \
        --no-cache-dir \
        -r requirements.txt \
    && rm -f requirements.txt

COPY --chmod=0755 docker/app.py  ./

CMD ["python","app.py"]
