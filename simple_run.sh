#!/usr/bin/env bash

PORT=18433
PARTITION="RTX3090"
TIME=0-01:00:00

while [[ "$1" =~ ^- && ! "$1" == "--" ]]; do case $1 in
  -h | --help )
    echo "
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
JOB_NAME="kiba-d_evaluation_$UUID"


echo "============================================="
echo ">>> USING PARTITION $PARTITION"
echo ">>> MAX TIME $TIME"
echo ">>> SUBMITTED $(date)"
echo ">>> UV_ARGS $UV_ARGS"
echo ">>> JOB_NAME $JOB_NAME"
echo "============================================="

srun --partition=$PARTITION \
     --job-name="$JOB_NAME" \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --oversubscribe \
     --time=$TIME \
     uv run -w vllm --cache-dir /netscratch/$USER/cache/uv \
         vllm serve "$VLLM_ARGS" \
             --download-dir=/ds/models/llms/cache \
             --port=$PORT&

squeue --name="$JOB_NAME"
SERVER="$(squeue --name="$JOB_NAME" -O NODELIST -h | awk '{$1=$1};1')"
VLLM_ENDPOINT="http://${SERVER}.kl.dfki.de:${PORT}/v1"

echo "waiting for vllm startup"
until curl --output /dev/null --silent --fail "${VLLM_ENDPOINT}/models"; do
    printf '.'
    sleep 5
    SERVER="$(squeue --name="$JOB_NAME" -O NODELIST -h | awk '{$1=$1};1')"
    VLLM_ENDPOINT="http://${SERVER}.kl.dfki.de:${PORT}/v1"
done
echo "vllm has started"

echo "we'd be running uv here"
uv run "$UV_ARGS"
echo "döner"

# WE NEED TO KILL THE JOB EXPLICITLY
scancel --name=$JOB_NAME
