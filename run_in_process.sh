#!/usr/bin/env bash

# default options that can be overridden by the use of flags
# random port per default to prevent script interference.
#export PORT=$(shuf -i 10000-60000 -n 1)  # only ports forwarded through vpn
PARTITION="RTXA6000-SLT"
TIME=1-00:00:00
N_GPUS=1

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
  -ng | --n-gpus )
    shift; N_GPUS=$1
    ;;
esac; shift; done
if [[ "$1" == '--' ]]; then shift; fi

export HF_HOME="/netscratch/$USER/cache/hf"
export VLLM_CACHE_ROOT="/netscratch/$USER/cache/vllm"
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"

# TODO what about SLURM cache etc that we used to have to configure, see e.g. https://github.com/DFKI-NLP/pegasus-bridle/?tab=readme-ov-file#boom-important-boom

# use uuid to prevent job collision
UUID="$(uuidgen)"
JOB_NAME="kiba-d_$UUID"

echo "============================================="
echo ">>> USING PARTITION $PARTITION"
echo ">>> MAX TIME $TIME"
echo ">>> SUBMITTED $(date)"
echo ">>> UV_ARGS --cache-dir $UV_CACHE_DIR $UV_ARGS"
echo ">>> JOB_NAME $JOB_NAME"
echo "============================================="

job(){
    echo ">>> START UV: uv run --cache-dir $UV_CACHE_DIR $UV_ARGS"
    uv run --cache-dir $UV_CACHE_DIR $UV_ARGS
    echo ">>> DONE WITH UV"
}

export -f job

srun --partition=$PARTITION \
     --job-name="$JOB_NAME" \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=$N_GPUS \
     --mem=128G \
     --oversubscribe \
     --time=$TIME \
     bash -c job
