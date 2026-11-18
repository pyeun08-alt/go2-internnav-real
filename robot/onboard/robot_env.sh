#!/usr/bin/env bash
# Source this file in the shell used for the robot modules or client.
ROBOT_PACKAGE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_SETUP="${ROS_SETUP:-/opt/ros/foxy/setup.bash}"
CYCLONEDDS_WORKSPACE="${CYCLONEDDS_WORKSPACE:-${HOME}/cyclonedds_ws}"
if [[ ! -f "$ROS_SETUP" || ! -f "$CYCLONEDDS_WORKSPACE/install/setup.bash" ]]; then
    echo 'ROS_SETUP 또는 CYCLONEDDS_WORKSPACE의 설치 경로를 확인하세요.' >&2
    return 1
fi
source "$ROS_SETUP" || return $?
source "$CYCLONEDDS_WORKSPACE/install/setup.bash" || return $?
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_HOME="${CYCLONEDDS_HOME:-${CYCLONEDDS_WORKSPACE}/install/cyclonedds}"
export CYCLONEDDS_URI="${CYCLONEDDS_URI:-file://${ROBOT_PACKAGE_DIR}/config/cyclonedds.xml}"
