#!/usr/bin/env bash

# default options that can be overridden by the use of flags
# random port per default to prevent script interference.
PARTITION="RTXA6000-SLT"
TIME=1-00:00:00
N_GPUS=1

# immutable-code options
GIT_REF=""
SYNC_REMOTE=0

# snapshot base dir
RUN_BASE_DIR="${RUN_BASE_DIR:-}"   # empty means: decide later inside the job

# flag processing for setting vars and displaying help
while [[ "$1" =~ ^- && ! "$1" == "--" ]]; do case $1 in
  -h | --help )
    echo "
    Help for the in-process-vllm cluster startup script.
    --------------------------------------------------------------------------------
    It is recommended to pass flag values wrapped in quotes like '$0 ... -v \"model/id --trust-remote-code\" ...'

    -pa | --partition       Partition to run the job on.            default=$PARTITION
    -t  | --time            Max slurm jub runtime.                  default=$TIME
    -u  | --uv              uv args for the python script to run.
    -r  | --ref             Git ref (branch/tag/commit) to run from. default=current working tree
    -sr | --sync-remote     Run 'git fetch --prune --tags' before submitting.
    -bd | --base-dir        Base dir for snapshot checkout.         default=SLURM_TMPDIR or /netscratch/$USER/tmp
    -ng | --n-gpus          Number of GPUs.                         default=$N_GPUS
    "
    exit
    ;;
  -pa | --partition )
    shift; PARTITION=$1
    ;;
  -t | --time )
    shift; TIME=$1
    ;;
  -u | --uv )
    shift; export UV_ARGS=$1
    ;;
  -r | --ref )
    shift; GIT_REF=$1
    ;;
  -sr | --sync-remote )
    SYNC_REMOTE=1
    ;;
  -bd | --base-dir )
    shift; RUN_BASE_DIR=$1
    ;;
  -ng | --n-gpus )
    shift; N_GPUS=$1
    ;;
esac; shift; done
if [[ "$1" == '--' ]]; then shift; fi

export HF_HOME="/netscratch/$USER/cache/hf"
export VLLM_CACHE_ROOT="/netscratch/$USER/cache/vllm"
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"
export DEFAULT_RUN_BASE_DIR="/netscratch/$USER/tmp"

# Resolve repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Optional: sync remote refs before submitting
if [[ "$SYNC_REMOTE" == "1" ]]; then
  echo ">>> git fetch (submit node) in $REPO_ROOT"
  git -C "$REPO_ROOT" fetch --prune --tags
fi

# Validate ref early (fail before allocating GPUs)
if [[ -n "$GIT_REF" ]]; then
  git -C "$REPO_ROOT" rev-parse --verify "$GIT_REF^{commit}" >/dev/null \
    || { echo "ERROR: GIT_REF '$GIT_REF' is not a valid commit-ish in $REPO_ROOT"; exit 2; }
fi

# use uuid to prevent job collision
UUID="$(uuidgen)"
JOB_NAME="kiba-d_$UUID"

echo "============================================="
echo ">>> USING PARTITION $PARTITION"
echo ">>> MAX TIME $TIME"
echo ">>> SUBMITTED $(date)"
echo ">>> UV_ARGS --cache-dir $UV_CACHE_DIR $UV_ARGS"
echo ">>> JOB_NAME $JOB_NAME"
if [[ -n "$GIT_REF" ]]; then
  echo ">>> GIT_REF $GIT_REF"
else
  echo ">>> GIT_REF (none; using current working tree)"
fi
echo "============================================="

job(){
    # Safer bash: exit on error/unset var, and propagate failures through pipes
    set -euo pipefail

    # Make these available inside the srun/bash -c environment
    # (they should already be in the environment, but be explicit)
    : "${REPO_ROOT:?REPO_ROOT not set}"
    : "${JOB_NAME:?JOB_NAME not set}"

    # default to SLURM_TMPDIR if available, otherwise use /netscratch/$USER/tmp
    RUN_BASE_DIR="${RUN_BASE_DIR:-${SLURM_TMPDIR:-$DEFAULT_RUN_BASE_DIR}}"
    RUN_ROOT="$RUN_BASE_DIR/$JOB_NAME"
    SNAP_DIR="$RUN_ROOT/repo"
    mkdir -p "$RUN_ROOT"

    if [[ -n "${GIT_REF:-}" ]]; then
        echo ">>> Using git ref: ${GIT_REF}"
        echo ">>> Creating snapshot checkout in: $SNAP_DIR"

        # Local, fast clone sharing objects with original repo (no network needed)
        git clone --shared --no-checkout "$REPO_ROOT" "$SNAP_DIR"
        git -C "$SNAP_DIR" checkout --detach "$GIT_REF"

        echo ">>> Snapshot commit: $(git -C "$SNAP_DIR" rev-parse HEAD)"

        # Recreate top-level symlinks (e.g., data -> /netscratch/...)
        # If you need nested symlinks too, increase -maxdepth.
        while IFS= read -r -d '' link; do
          name="$(basename "$link")"
          if [[ ! -e "$SNAP_DIR/$name" ]]; then
            ln -s "$(readlink "$link")" "$SNAP_DIR/$name"
          fi
        done < <(find "$REPO_ROOT" -maxdepth 1 -type l -print0)

        cd "$SNAP_DIR"
    else
        echo ">>> No --ref provided; running from current working tree at: $REPO_ROOT"
        cd "$REPO_ROOT"
    fi

    COMMAND="uv run --cache-dir \"$UV_CACHE_DIR\" ${UV_ARGS:-}"
    echo ">>> START UV: $COMMAND"
    # use eval to properly handle the UV_ARGS with multiple arguments and quotes
    eval "$COMMAND"
    echo ">>> DONE WITH UV"
}

# Export the 'job' bash function so it is available in the new shell started by `srun ... bash -c job`.
export -f job

# Export needed vars for the srun environment
export JOB_NAME
export REPO_ROOT
export GIT_REF
export UV_ARGS
export RUN_BASE_DIR

srun --partition="$PARTITION" \
     --job-name="$JOB_NAME" \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task="$N_GPUS" \
     --mem=128G \
     --oversubscribe \
     --time="$TIME" \
     bash -c job
