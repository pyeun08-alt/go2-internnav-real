# 추론 PC 준비 및 실행

이 안내의 호스트 명령은 `~/go2-internnav/pc`에서 실행합니다. 컨테이너 내부의 프로젝트 위치는 `/workspace/InternNav`입니다. 개인 계정 이름과 관계없이 동일합니다.

## 1. 호스트 환경 및 이미지 준비 — PC 호스트

Linux x86_64와 NVIDIA GPU가 필요합니다. Docker 또는 GPU 런타임이 없으면 먼저 [Docker Engine 설치](https://docs.docker.com/engine/install/ubuntu/)와 [NVIDIA Container Toolkit 설치·Docker 설정](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)을 완료합니다.

```bash
cd ~/go2-internnav/pc
nvidia-smi
docker info
```

`nvidia-smi`에 GPU가 표시되고 `docker info`가 정상 출력되는지 확인합니다. Docker 소켓 권한 오류가 있으면 해당 PC의 Docker 사용 권한을 먼저 설정하거나, 아래 Docker 명령을 `sudo docker ...`로 실행합니다.

```bash
docker build -t go2-internnav:local .
docker run --rm --gpus all go2-internnav:local \
  python -c 'import torch, flash_attn; print(torch.__version__); print(torch.cuda.get_device_name(0)); assert torch.cuda.is_available()'
```

이미지는 Ubuntu 22.04/Python 3.10, PyTorch 2.8.0/CUDA 12.8, Flash Attention 2.8.3.post1을 사용합니다. 이 이미지는 x86_64 PC용이며 로봇 Jetson에서 빌드하지 않습니다. GPU 코드 로딩 검사는 모델 전체가 GPU 메모리에 들어가는지까지 확인하지는 않습니다.

## 2. 모델 및 컨테이너 준비 — PC 호스트

학습 완료 체크포인트 폴더를 별도로 전달받아 아래 `MODEL_SOURCE`에 지정합니다. 해당 폴더 안에 `config.json`, tokenizer 관련 파일, `model.safetensors.index.json`, 모든 가중치 shard가 함께 있어야 합니다.

```bash
cd ~/go2-internnav/pc
MODEL_SOURCE="/전달받은/체크포인트/폴더"
test -d "$MODEL_SOURCE" && test -f "$MODEL_SOURCE/config.json"
```

위 확인 명령이 성공한 뒤 복사합니다. 기존 대상 폴더가 있다면 서로 다른 모델의 파일을 섞지 말고 폴더 전체를 별도 위치에 보관한 뒤 새로 복사합니다.

```bash
mkdir -p InternNav/checkpoints InternNav/test_data
if [ ! -e InternNav/checkpoints/Go2_nextdit_finetuned ]; then
  cp -a "$MODEL_SOURCE" InternNav/checkpoints/Go2_nextdit_finetuned
else
  echo "대상 모델 폴더가 이미 있습니다. 기존 모델을 사용할지 확인하세요."
fi
```

PC 호스트에서 다음 명령으로 컨테이너를 시작합니다. 호스트의 현재 사용자 권한으로 동작하므로 기록 파일도 해당 사용자 소유로 저장됩니다.

```bash
docker run --rm -it --gpus all --network host --shm-size 8g \
  --name go2-internnav \
  --user "$(id -u):$(id -g)" \
  -e HF_HOME=/tmp/huggingface -e XDG_CACHE_HOME=/tmp/cache \
  -v "$PWD/InternNav:/workspace/InternNav" \
  go2-internnav:local
```

이후 3절까지는 **컨테이너 내부 터미널**입니다. 컨테이너 종료 후 재실행할 때도 위 명령을 사용하며, 마운트된 모델과 실행 기록은 유지됩니다. 이름이 이미 사용 중이면 `docker ps -a --filter name=go2-internnav`로 확인하고, 기존 실행을 사용하려면 `docker exec -it go2-internnav bash`로 접속합니다.

## 3. 모델 확인 및 서버 실행 — PC 컨테이너

```bash
cd /workspace/InternNav
python - <<'PYCODE'
import json
from pathlib import Path
p = Path('checkpoints/Go2_nextdit_finetuned')
config = json.loads((p / 'config.json').read_text())
assert config.get('system1') == 'nextdit_async', 'nextdit_async 체크포인트를 사용하세요.'
index = json.loads((p / 'model.safetensors.index.json').read_text())
missing = [name for name in set(index['weight_map'].values()) if not (p / name).is_file()]
assert not missing, f'가중치 파일 누락: {missing}'
from transformers import AutoProcessor
AutoProcessor.from_pretrained(str(p), local_files_only=True)
print('모델 설정·가중치 파일 목록·tokenizer/processor 확인 완료')
PYCODE
```

RGB 특징 추출에 사용하는 Depth Anything 가중치를 다운로드합니다. 이미 내려받은 경우 같은 명령을 다시 실행해도 사용할 수 있습니다.

```bash
hf download depth-anything/Depth-Anything-V2-Metric-Hypersim-Small \
  depth_anything_v2_metric_hypersim_vits.pth --local-dir checkpoints
```

실제 이동 지시문을 영어로 설정하고 서버를 실행합니다.

```bash
export NAV_INSTRUCTION="Walk forward and stop next to the sofa."
export MODEL_PATH=checkpoints/Go2_nextdit_finetuned
bash /opt/start_server.sh
```

모델 로딩과 초기 추론 후 `Running on http://127.0.0.1:5801`이 표시될 때까지 기다립니다. 예시 지시문은 실제 출발 위치와 목적지에 맞게 바꿉니다. `CUDA out of memory`이면 다른 GPU 작업의 메모리 사용과 모델을 올릴 수 있는 GPU 메모리 용량을 확인합니다.

이 서버 터미널은 실행 상태로 유지합니다. 기록은 PC의 `pc/InternNav/test_data/`에 저장됩니다.

기존에 동일한 패키지가 설치된 `internnav-realworld` Conda 환경을 재사용하는 경우에만, **PC 호스트**에서 다음 방법을 사용할 수 있습니다. 처음 설치하는 사용자는 위 Docker 절차를 사용합니다.

```bash
cd ~/go2-internnav/pc
conda activate internnav-realworld
export NAV_INSTRUCTION="Walk forward and stop next to the sofa."
export MODEL_PATH=checkpoints/Go2_nextdit_finetuned
bash start_server.sh
```

## 4. SSH 역방향 터널 — PC의 별도 호스트 터미널

`GO2_IP`는 Go2 제어부의 `192.168.123.161`이 아니라 **로봇 Jetson의 현재 Wi-Fi 접속 주소**입니다. 로봇에서 `ip -br addr`로 확인합니다.

```bash
GO2_IP="로봇 Jetson의 현재 Wi-Fi IP"
ssh "unitree@${GO2_IP}"
```

처음 접속할 때는 장비의 호스트 키를 확인하고 로그인합니다. 접속이 확인되면 `exit`로 PC에 돌아온 뒤 아래 명령을 실행합니다. 암호 인증 또는 사용자 SSH 키를 사용하며, 키·암호는 저장소에 포함하지 않습니다.

```bash
ssh -NT \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -R 127.0.0.1:5801:127.0.0.1:5801 \
  "unitree@${GO2_IP}"
```

정상 연결되면 출력 없이 대기합니다. 이 터미널을 유지한 상태로 [로봇 안내 4절](../robot/README.md#4-온보드-모듈과-클라이언트-실행)을 진행합니다. 컨테이너는 host 네트워크를 사용하므로 SSH 터널은 PC 호스트에서 열 수 있습니다.

`remote port forwarding failed for listen port 5801`이면 [로봇 안내의 포트 충돌 처리](../robot/README.md#5801-포트-충돌)를 수행하고 다시 연결합니다.

사용한 오픈소스 패키지와 버전은 [OpenSW_List.txt](OpenSW_List.txt)에 정리했습니다.
