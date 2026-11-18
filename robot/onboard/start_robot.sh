#!/bin/bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/robot_env.sh" || exit $?

# ================= CONFIGURATION =================
# Select the wired robot interface; override with ROBOT_IF. Default: eth1.
ROBOT_IF="${ROBOT_IF:-eth1}"
# =================================================

PID_DRIVER=""
PID_BRIDGE=""
PID_CAMERA=""

# Function to kill all background processes when Ctrl+C is pressed
cleanup() {
    trap - SIGINT SIGTERM
    echo ""
    echo "========================================="
    echo "   Stopping all robot modules..."
    echo "========================================="
    for pid in "$PID_CAMERA" "$PID_BRIDGE" "$PID_DRIVER"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    exit 0
}

# Trap SIGINT (Ctrl+C) to run the cleanup function
trap cleanup SIGINT SIGTERM

echo "========================================="
echo "   Launching OpenLegged Robot System"
echo "========================================="
echo "   Target Interface: $ROBOT_IF"
echo "========================================="

# 1. Start the Unitree Driver (Bottom Layer)
# We pass the interface variable ($ROBOT_IF) to the python script
echo "[1/3] Starting Unitree Driver..."
python3 "$SCRIPT_DIR/unitree_driver.py" "$ROBOT_IF" &
PID_DRIVER=$!
sleep 3  # Wait for the robot to stand up

# 2. Start the ROS Bridge
echo "[2/3] Starting ROS Bridge..."
python3 "$SCRIPT_DIR/ros_bridge.py" &
PID_BRIDGE=$!
sleep 1

# 3. Start RealSense Publisher
# Assuming your file is named realsense_publisher.py
echo "[3/3] Starting RealSense Publisher..."
if [ -f "$SCRIPT_DIR/realsense_publisher.py" ]; then
    python3 "$SCRIPT_DIR/realsense_publisher.py" &
    PID_CAMERA=$!
else
    echo "[Warning] realsense_publisher.py not found, skipping."
fi

echo "========================================="
echo "   All Systems GO! Press Ctrl+C to stop."
echo "========================================="

# Keep the script running to maintain the trap
wait
