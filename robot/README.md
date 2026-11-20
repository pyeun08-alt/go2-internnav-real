# 로봇 Jetson 준비 및 실행

아래 명령은 **로봇 Jetson 터미널**에서 실행합니다. 코드 위치는 `~/go2-internnav/robot`을 기준으로 합니다. 모델과 PC용 PyTorch는 로봇에 설치하지 않습니다.

## 1. 기존 시스템 환경 확인

ROS 2 Foxy/Python 3.8, CycloneDDS 본체, RealSense 시스템 라이브러리가 설치된 Go2 Jetson을 사용합니다. 기본 위치를 먼저 확인합니다.

```bash
cd ~/go2-internnav/robot
ls /opt/ros/foxy/setup.bash
ls ~/cyclonedds_ws/install/setup.bash
```

설치 경로가 다르면 **로봇 터미널을 새로 열 때마다**, 환경 파일을 불러오기 전에 실제 위치를 지정합니다.

```bash
# 기본 위치에 설치되어 있으면 이 두 줄은 생략합니다.
export ROS_SETUP="/실제/ROS/설치위치/setup.bash"
export CYCLONEDDS_WORKSPACE="/실제/cyclonedds_ws"
```

환경을 적용하고 기본 모듈을 확인합니다.

```bash
source onboard/robot_env.sh
python3 --version
python3 -c 'import rclpy, cv_bridge, message_filters, cv2, numpy, scipy, requests; from PIL import Image'
dpkg-query -W 'librealsense2*'
```

Python 3.8 및 ROS 모듈이 정상 로딩되는지 확인합니다. 수집된 실행 환경의 RealSense 시스템 라이브러리는 2.54.2입니다. 위 시스템 구성요소가 없다면 이 추가 패키지 절차만으로 설치가 완료되지 않으므로 해당 Jetson의 기존 설치 환경을 먼저 복원·준비해야 합니다.

DDS 설정은 `config/cyclonedds.xml`을 사용합니다. 기존 셸에 `CYCLONEDDS_URI`가 설정되어 있으면 그 값이 우선합니다. 패키지 설정을 사용하려면 `unset CYCLONEDDS_URI` 후 `source onboard/robot_env.sh`를 다시 실행합니다.

## 2. 추가 Python 패키지

```bash
cd ~/go2-internnav/robot
source onboard/robot_env.sh
python3 -m pip install --user -r requirements.txt
python3 -m pip install --user --no-deps -e vendor/unitree_sdk2_python
python3 -c 'import cyclonedds, pyrealsense2, casadi, unitree_sdk2py'
```

ROS와 동일한 시스템 `python3`를 사용합니다. `requirements.txt`는 CycloneDDS Python 바인딩 0.10.2, RealSense 바인딩 2.54.2.5684, CasADi 3.7.2를 지정합니다. NumPy·SciPy·Pillow·requests·OpenCV는 1절에서 확인한 기존 설치를 사용합니다.

## 3. eth0 / eth1 및 유선 IP 확인

```bash
ip -br addr
ip -br link show eth0
ip -br link show eth1
ip route get 192.168.123.161
```

- `LOWER_UP`: 물리 연결 있음. 로봇 케이블이 연결된 포트인지 확인합니다.
- `NO-CARRIER`: 케이블·장치 연결을 먼저 확인합니다.
- 로봇에 연결된 유선 포트 한 곳에만 `192.168.123.222/24`를 설정합니다.
- 경로 결과가 `dev eth0` 또는 `dev eth1`, `src 192.168.123.222`인지 확인합니다. `via ... dev wlan0`이면 유선 연결·주소를 다시 확인합니다.

실제 연결된 인터페이스 하나를 지정합니다.

```bash
ROBOT_IF=eth1
# 실제 연결이 eth0이면 ROBOT_IF=eth0
```

### 유선 주소가 없는 경우

`ip -br addr`에서 **eth0와 eth1 모두에 해당 주소가 없을 때만** 추가합니다.

```bash
sudo ip link set dev "$ROBOT_IF" up
sudo ip addr add 192.168.123.222/24 dev "$ROBOT_IF"
```

이미 선택한 인터페이스에 주소가 있으면 추가하지 않습니다. 다른 포트에 주소가 남아 있으면 아래 주소 이동 절차를 적용합니다.

### 다른 포트에 주소가 남은 경우

로봇 클라이언트·온보드 모듈을 종료하고, SSH가 Wi-Fi로 연결된 상태에서 필요한 방향 하나만 실행합니다. 출발 포트에 해당 주소가 있고 도착 포트에는 없는지 먼저 확인합니다.

```bash
# eth0 → eth1
sudo ip addr del 192.168.123.222/24 dev eth0 && \
  sudo ip addr add 192.168.123.222/24 dev eth1
```

```bash
# eth1 → eth0
sudo ip addr del 192.168.123.222/24 dev eth1 && \
  sudo ip addr add 192.168.123.222/24 dev eth0
```

### 경로·응답 확인

```bash
ip route get 192.168.123.161
ping -c 3 -W 2 -I "$ROBOT_IF" 192.168.123.161
```

선택한 포트와 `src 192.168.123.222`가 표시되고 로봇 응답이 오는지 확인합니다. `ip addr` 변경은 임시 설정이므로 재부팅 후 다시 확인합니다.

## 4. 온보드 모듈과 클라이언트 실행

[PC 서버와 SSH 터널](../pc/README.md)을 먼저 실행합니다. 로봇 주변 이동 공간을 확보하고 조종기를 준비합니다.

**로봇 터미널 1 — 드라이버·센서·브리지:**

```bash
cd ~/go2-internnav/robot
# 1절에서 설치 경로를 별도 지정했다면 이 터미널에도 먼저 적용합니다.
ROBOT_IF=eth1 bash onboard/start_robot.sh
```

실제 연결이 `eth0`이면 위 명령을 `ROBOT_IF=eth0`으로 바꿉니다. 이 명령은 로봇 드라이버를 실제로 실행합니다.

**로봇 터미널 2 — 통신·센서 확인:**

```bash
cd ~/go2-internnav/robot
source onboard/robot_env.sh
curl --max-time 5 -sS -o /dev/null -w 'HTTP %{http_code}\n' \
  http://127.0.0.1:5801/eval_dual
```

서버가 정상 연결되면 GET 요청에 **HTTP 405**가 반환됩니다. 이어서 각 토픽에서 메시지가 들어오는지 확인하고 Ctrl+C로 빠져나옵니다.

```bash
ros2 topic hz /camera/camera/color/image_raw
```

```bash
ros2 topic hz /camera/camera/aligned_depth_to_color/image_raw
```

```bash
ros2 topic hz /odom_bridge
```

카메라·depth·odometry 수신과 서버 연결이 확인되면 같은 터미널에서 클라이언트를 실행합니다.

```bash
bash start_client.sh
```

클라이언트는 `http://127.0.0.1:5801/eval_dual`에 관측을 보내고 제어 명령을 발행합니다. 종료 시 클라이언트를 Ctrl+C로 종료한 뒤 온보드 모듈을 종료합니다. 이동 중 즉시 정지가 필요하면 조종기로 정지합니다.

## 5. 자주 발생하는 오류

### 5801 포트 충돌

PC의 SSH 명령에서 `remote port forwarding failed for listen port 5801`이 발생하면, 기존 터널이 남아 있는지 확인합니다. 로봇 클라이언트를 종료하고 이 포트를 사용하는 기존 터널을 정리할 때 **로봇 터미널**에서 실행합니다.

```bash
sudo ss -H -ltnp 'sport = :5801' \
  | sed -n 's/.*"sshd",pid=\([0-9]\+\).*/\1/p' \
  | sort -u \
  | xargs -r sudo kill -TERM
```

5801을 수신하는 sshd 프로세스만 종료합니다. 이후 PC에서 SSH 터널을 다시 연결하고 HTTP 405를 확인합니다.

| 증상 | 확인 및 조치 |
| --- | --- |
| `curl` 실패·HTTP 000 | PC 서버 로딩 완료, PC→Jetson SSH 연결, 역방향 터널 유지 상태 확인 |
| `ModuleNotFoundError` | 같은 로봇 터미널에 `robot_env.sh` 적용. 시스템 Python 3.8과 1~2절 모듈 확인 |
| 카메라 영상 미수신 | D435i USB·전원과 중복 카메라 실행 확인 후 온보드 모듈 재실행 |
| odometry 미수신·`skip planning` | 유선 포트·IP·ping, `ROBOT_IF`, 드라이버·브리지 출력 확인 |
| 서버 추론 오류·시간 초과 | 클라이언트 종료 후 PC 서버 로그 확인. 오류 원인을 해결하고 서버·클라이언트를 새로 실행 |

사용한 오픈소스 패키지와 버전은 [OpenSW_List.txt](OpenSW_List.txt)에 정리했습니다.
