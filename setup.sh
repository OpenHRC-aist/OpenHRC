#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_FILE="${SCRIPT_DIR}/ohrc_repos.repos"
WS_SRC="$(dirname "${SCRIPT_DIR}")"

# Robot -> repositories (keys in ohrc_repos.repos) required for that robot.
ROBOTS=(franka xarm)
declare -A ROBOT_REPOS=(
    [franka]="franka_ros2 franka_description"
    [xarm]="xarm_ros2"
)

select_interactive() {
    echo "Select the robots to install (space-separated numbers):" >&2
    echo "  0) all" >&2
    local i
    for i in "${!ROBOTS[@]}"; do
        printf "  %d) %s\n" "$((i + 1))" "${ROBOTS[$i]}" >&2
    done
    local reply
    read -rp "> " reply
    [[ -z "${reply// /}" || "$reply" =~ ^[[:space:]]*0[[:space:]]*$ ]] && { echo all; return; }
    local picks=()
    for i in $reply; do
        if [[ "$i" =~ ^[0-9]+$ ]] && (( i >= 1 && i <= ${#ROBOTS[@]} )); then
            picks+=("${ROBOTS[$((i - 1))]}")
        else
            echo "Invalid selection: $i" >&2
            return 1
        fi
    done
    printf '%s\n' "${picks[@]}"
}

if [[ $# -eq 0 ]]; then
    if [[ -t 0 ]]; then
        mapfile -t SELECTED < <(select_interactive)
        [[ ${#SELECTED[@]} -gt 0 ]] || exit 1
    else
        SELECTED=(all)
    fi
else
    case "$1" in
        -h|--help) usage; exit 0 ;;
    esac
    SELECTED=("$@")
fi

if [[ " ${SELECTED[*]} " == *" all "* ]]; then
    SELECTED=("${ROBOTS[@]}")
fi

for robot in "${SELECTED[@]}"; do
    if [[ -z "${ROBOT_REPOS[$robot]+x}" ]]; then
        echo "Unknown robot: '$robot'" >&2
        usage >&2
        exit 1
    fi
done

# De-duplicate while keeping order.
mapfile -t SELECTED < <(printf '%s\n' "${SELECTED[@]}" | awk '!seen[$0]++')

has_robot() { [[ " ${SELECTED[*]} " == *" $1 "* ]]; }

REPOS=()
for robot in "${SELECTED[@]}"; do
    read -ra r <<< "${ROBOT_REPOS[$robot]}"
    REPOS+=("${r[@]}")
done

TOTAL=1
has_robot franka && TOTAL=$((TOTAL + 1))
has_robot xarm && TOTAL=$((TOTAL + 2))
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

echo "Starting setup for: ${SELECTED[*]}"
cd "${WS_SRC}"

# vcs import has no name filter, so feed it a filtered copy of the .repos file.
python3 - "${REPOS_FILE}" "${REPOS[@]}" <<'PY' | vcs import .
import sys
import yaml

path, wanted = sys.argv[1], sys.argv[2:]
with open(path) as f:
    repos = yaml.safe_load(f)["repositories"]
missing = [name for name in wanted if name not in repos]
if missing:
    sys.exit(f"Not found in {path}: {', '.join(missing)}")
yaml.safe_dump({"repositories": {name: repos[name] for name in wanted}},
               sys.stdout, sort_keys=False)
PY
progress "Imported repos: ${REPOS[*]}"

if has_robot franka; then
    touch franka_ros2/franka_mobile_sensors/COLCON_IGNORE
    progress "Created COLCON_IGNORE"
fi

if has_robot xarm; then
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
fi

echo "Done."
