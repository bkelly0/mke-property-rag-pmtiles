# Stage 1: build tippecanoe from source
FROM debian:bookworm-slim AS tippecanoe-build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    zlib1g-dev \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 https://github.com/felt/tippecanoe.git .
RUN make -j"$(nproc)" && make install PREFIX=/usr/local

# Stage 2: runtime image
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY --from=tippecanoe-build /usr/local/bin/tippecanoe /usr/local/bin/tippecanoe
COPY --from=tippecanoe-build /usr/local/bin/tippecanoe-decode /usr/local/bin/tippecanoe-decode
COPY --from=tippecanoe-build /usr/local/bin/tile-join /usr/local/bin/tile-join

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENTRYPOINT ["python", "main.py"]
