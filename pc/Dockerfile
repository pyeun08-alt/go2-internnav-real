FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-dev build-essential git ca-certificates \
    openssh-client curl libglib2.0-0 libgl1 libxcb1 \
    && rm -rf /var/lib/apt/lists/*
RUN python3.10 -m venv /opt/internnav
ENV PATH="/opt/internnav/bin:${PATH}"
RUN python -m pip install --upgrade pip \
    && python -m pip install setuptools==84.0.0 wheel==0.48.0 \
       setuptools-scm==8.3.1 packaging==24.2 numpy==1.26.4
RUN python -m pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
    --index-url https://download.pytorch.org/whl/cu128
COPY requirements-runtime.txt /tmp/requirements-runtime.txt
RUN python -m pip install --no-deps --no-build-isolation -r /tmp/requirements-runtime.txt
COPY InternNav /workspace/InternNav
WORKDIR /workspace/InternNav
RUN python -m pip install --no-deps --no-build-isolation -e . \
    && python -m pip check
ENV PYTHONPATH=/workspace/InternNav
COPY start_server.sh /opt/start_server.sh
EXPOSE 5801
CMD ["bash"]
