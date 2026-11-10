# Tools to prepare the data: the 2013 dump converter.
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl xz-utils pbzip2 \
 && rm -rf /var/lib/apt/lists/*
COPY convert-2013.py convert-2013.sh /usr/local/bin/
