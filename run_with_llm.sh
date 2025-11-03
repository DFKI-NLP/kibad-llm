#!/usr/bin/env bash

# default options that can be overridden by the use of flags
# random port per default to prevent script interference.
PORT=$(shuf -i 10000-60000 -n 1)  # only ports forwarded through vpn
PARTITION="RTXA6000-SLT"
TIME=0-01:00:00

# flag processing for setting vars and displaying help
while [[ "$1" =~ ^- && ! "$1" == "--" ]]; do case $1 in
  -h | --help )
    echo "
    Help for the all in one cluster startup script.
    --------------------------------------------------------------------------------
    It is recommended to pass flag values wrapped in quotes like '$0 ... -v \"model/id --trust-remote-code\" ...'

    -v / --vllm         Arguments with which to run vLLM.
    -po / --port        Port to run vLLM on.                    default=$PORT
    -pa / --partition   Partition to run vLLM on.               default=$PARTITION
    -t / --time         Max slurm jub runtime.                  default=$TIME
    -u / --uv           uv args for the python script to run.
    "
    exit
    ;;
  -v | --vllm )
    shift; VLLM_ARGS=$1
    ;;
  -po | --port )
    shift; PORT=$1
    ;;
  -pa | --partition )
    shift; PARTITION=$1
    ;;
  -t | --time )
    shift; TIME=$1
    ;;
  -u | --uv )
    shift; UV_ARGS=$1
    ;;
esac; shift; done
if [[ "$1" == '--' ]]; then shift; fi

export HF_HOME="/netscratch/$USER/.cache/hf"

UUID="$(uuidgen)"
JOB_NAME="kiba-d_$UUID"

echo "============================================="
echo ">>> USING PARTITION $PARTITION"
echo ">>> MAX TIME $TIME"
echo ">>> SUBMITTED $(date)"
echo ">>> VLLM_ARGS $VLLM_ARGS --download-dir=/ds/models/llms/cache --port=$PORT"
echo ">>> UV_ARGS $UV_ARGS"
echo ">>> JOB_NAME $JOB_NAME"
echo "============================================="

export VLLM_CONFIGURE_LOGGING=0

srun --partition=$PARTITION \
     --job-name="$JOB_NAME" \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --oversubscribe \
     --time=$TIME \
     uvx --cache-dir /netscratch/$USER/cache/uv \
         vllm serve "$VLLM_ARGS" \
             --download-dir=/ds/models/llms/cache \
             --port=$PORT&

SERVER="$(squeue --name="$JOB_NAME" -O NODELIST -h | awk '{$1=$1};1')"
# !the name LLM_API_BASE is important as the extractors hydra config looks for it!
export LLM_API_BASE="http://${SERVER}.kl.dfki.de:${PORT}/v1"

echo ">>> WAITING FOR VLLM STARTUP"
until curl --output /dev/null --silent --fail "${LLM_API_BASE}/models"; do
    printf '.'
    sleep 5
    SERVER="$(squeue --name="$JOB_NAME" -O NODELIST -h | awk '{$1=$1};1')"
    export LLM_API_BASE="http://${SERVER}.kl.dfki.de:${PORT}/v1"
done
echo ">>> VLLM HAS STARTED"

echo ">>> START UV: uv run $UV_ARGS"
uv run $UV_ARGS
echo ">>> DONE WITH UV"

# the job needs to be killed explicitly in some cases.
scancel --name=$JOB_NAME
