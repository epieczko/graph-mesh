FROM python:3.10-slim

WORKDIR /app
# copy requirements file only if it exists, ignore poetry files
COPY requirements.txt ./requirements.txt

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .

# ENTRYPOINT ["python", "-m", "graph_mesh_orchestrator.pipeline"]
