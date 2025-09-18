# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Keep base image minimal (avoid compilers unless wheels fail)
RUN apt-get update && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy only required runtime files to shrink context
COPY app.py advanced_models.py model_loader.py models.py week2_feature_engineering_fixed.py ./
COPY app_core ./app_core
COPY templates ./templates
COPY static ./static
COPY dataset_metadata_fixed.json feature_scaler.pkl target_scaler.pkl ./
# Using PyTorch artifact for now; switch to ONNX in later phase
COPY best_attentionlstm_*.pth ./

# Create necessary directories (static already copied; avoid creating /app/models
# which can shadow the Python module `models.py` and break imports)
RUN mkdir -p /app/static

ENV OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1
EXPOSE 8000

# Health check without curl (use Python stdlib)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request,sys; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health'); sys.exit(0)" || exit 1

# Run the application honoring $PORT and configurable workers
CMD ["sh","-c","exec gunicorn app_core.main:app --workers ${WORKERS:-2} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --access-logfile - --log-level info"]
