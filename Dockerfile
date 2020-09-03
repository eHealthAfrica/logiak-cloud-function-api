FROM python:3.8-slim-buster

RUN apt-get update -qq && \
    apt-get -qq \
        --yes \
        --allow-downgrades \
        --allow-remove-essential \
        --allow-change-held-packages \
        install gcc && \
    pip install -q --upgrade pip

RUN mkdir /test
WORKDIR /test
COPY ./test/conf/requirements.txt /test/requirements.txt
RUN pip install -q --upgrade pip && \
    pip install -q -r /test/requirements.txt
COPY ./test/* /test/
COPY ./*.py /test/app/
COPY ./mock /test/app/mock
COPY ./cloud /test/app/cloud
