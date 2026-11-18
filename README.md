# Go2 실로봇 내비게이션

외부 GPU PC에서 NextDiT 기반 모델을 실행하고, 로봇 Jetson에서 카메라·odometry 수신과 PID/MPC 주행 제어를 수행합니다. 수정된 코드가 포함되어 있으므로 원본 저장소를 별도로 받은 뒤 패치를 적용할 필요가 없습니다.

## 1. 필요한 환경과 자료

| 위치 | 준비 항목 |
| --- | --- |
| 추론 PC | Linux x86_64, NVIDIA GPU/드라이버, Docker Engine, NVIDIA Container Toolkit |
| 로봇 Jetson | 기존 ROS 2 Foxy/Python 3.8, CycloneDDS 빌드, RealSense 시스템 라이브러리, Go2 및 D435i 연결 |
| 모델 | `system1=nextdit_async`인 학습 완료 체크포인트 전체 폴더. Git 저장소에는 포함하지 않음 |
| 연결 | PC에서 로봇 Jetson으로 SSH 접속 가능, Jetson과 Go2 사이 유선 연결 |

학습 완료 체크포인트는 별도로 전달받아 준비합니다. 체크포인트는 설정 파일뿐 아니라 모든 `.safetensors` 가중치가 있어야 합니다.

이 안내는 기존 ROS·CycloneDDS·RealSense가 설치된 Go2 Jetson을 대상으로 합니다. 빈 Jetson에 해당 시스템 소프트웨어를 처음 설치하는 절차는 포함하지 않습니다. 실행 전 확인 방법은 [로봇 안내](robot/README.md)에 있습니다.

## 2. 코드 받기

PC 호스트와 로봇 Jetson에서 각각 실행합니다.

```bash
REPO_URL="https://github.com/pyeun08-alt/go2-internnav-real.git"
git clone "$REPO_URL" "$HOME/go2-internnav"
cd "$HOME/go2-internnav"
```

위 명령은 로컬 폴더 이름을 `go2-internnav`로 지정합니다. 다른 위치에 배치한 경우 이후 명령의 `~/go2-internnav`만 그 위치로 바꿉니다. 외부 소스가 폴더 안에 포함되어 있으므로 별도의 `git submodule update`는 실행하지 않습니다.

## 3. 준비와 실행 순서

1. [로봇 안내](robot/README.md)의 1~3절에서 기존 환경·추가 패키지·유선 연결을 준비합니다.
2. [PC 안내](pc/README.md)의 1~3절에서 Docker 이미지·모델을 준비하고 서버를 실행합니다.
3. [PC 안내](pc/README.md)의 4절에서 SSH 역방향 터널을 연결합니다.
4. [로봇 안내](robot/README.md)의 4절에서 온보드 모듈·센서 수신을 확인하고 클라이언트를 실행합니다.

각 코드 블록 앞의 **PC 호스트 / PC 컨테이너 / 로봇 터미널** 구분을 따라 실행합니다. 종료 순서는 로봇 클라이언트 → 온보드 모듈 → SSH 터널 → PC 서버입니다.

## 폴더 구성

```text
robot/
  README.md              로봇 준비·연결·실행·오류 대응
  requirements.txt       기존 Jetson에 추가할 Python 패키지
  start_client.sh        클라이언트 실행
  client/                HTTP 클라이언트, PID/MPC, 스레드 유틸리티
  onboard/               센서 발행, ROS–UDP 브리지, Unitree 드라이버
  config/                CycloneDDS 설정
  vendor/                Unitree SDK 소스
  licenses/              원본 라이선스
pc/
  README.md              PC 준비·모델·서버·SSH 터널 안내
  Dockerfile             x86_64 추론 환경
  requirements-runtime.txt
  start_server.sh        모델 서버 실행
  InternNav/             NextDiT 추론 코드와 필요한 인코더
```

## 코드 출처

- [InternNav](https://github.com/InternRobotics/InternNav): [LICENSE](pc/InternNav/LICENSE)
- [InternNav-deploy](https://github.com/cmjang/InternNav-deploy): [LICENSE](robot/licenses/InternNav-deploy.LICENSE)
- [Unitree SDK2 Python](https://github.com/unitreerobotics/unitree_sdk2_python): [LICENSE](robot/vendor/unitree_sdk2_python/LICENSE)

각 외부 소스의 라이선스·출처 파일은 해당 디렉터리에 포함되어 있습니다. 학습·시뮬레이션·예제는 제외되어 있으며, 실로봇 실행 절차는 위 장비별 README를 기준으로 합니다.
