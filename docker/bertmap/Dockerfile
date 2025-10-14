FROM python:3.10-slim
LABEL org.opencontainers.image.source="https://github.com/example/graph-mesh"

RUN useradd -ms /bin/bash runner
WORKDIR /opt/bertmap

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY bertmap/ /opt/bertmap/

USER runner
ENTRYPOINT ["python", "-m", "bertmap.cli"]
