#!/bin/bash
set -euo pipefail

TOTAL=4
STEP=0

progress() {
    STEP=$((STEP + 1))
    local width=30
    local filled=$((STEP * width / TOTAL))
    local empty=$((width - filled))
    printf "\n[%s%s] %d/%d  %s\n" \
        "$(printf '#%.0s' $(seq 1 $filled))" \
        "$(printf -- '-%.0s' $(seq 1 $empty) 2>/dev/null)" \
        "$STEP" "$TOTAL" "$1"
}

echo "Starting setup..."

vcs import . < OpenHRC/ohrc_repos.repos
progress "Imported repos"

touch franka_ros2/franka_mobile_sensors/COLCON_IGNORE
progress "Created COLCON_IGNORE"

(
    cd xarm_ros2
    git submodule update --init --recursive --progress
)
progress "Initialized xarm_ros2 submodules"

(
    cd xarm_ros2
    git pull --recurse-submodules --progress
)
progress "Pulled xarm_ros2 updates"

echo "Done."