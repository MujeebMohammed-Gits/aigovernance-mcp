FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Ensure /app is on PYTHONPATH so internal_llm_api is importable
ENV PYTHONPATH=/app

CMD ["uvicorn", "internal_llm_api.server:app", "--host", "0.0.0.0", "--port", "8000"]
