FROM python:3.10-slim

WORKDIR /app
# copy the pip requirements list (poetry files are optional in this image)
COPY requirements.txt ./requirements.txt

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .

ENTRYPOINT ["python", "-m", "graph_mesh_orchestrator.pipeline"]
