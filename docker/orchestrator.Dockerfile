FROM python:3.10-slim

WORKDIR /app
COPY pyproject.toml poetry.lock* requirements.txt* ./

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi \
    && if [ -f pyproject.toml ]; then pip install --no-cache-dir .; fi

COPY . .

ENTRYPOINT ["python", "-m", "graph_mesh_orchestrator.pipeline"]
