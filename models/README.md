# How-To Run an LLM on the DFKI Cluster

- [How-To Run an LLM on the DFKI Cluster](#how-to-run-an-llm-on-the-dfki-cluster)
  - [Quickstart](#quickstart)
    - [Prerequisites](#prerequisites)
    - [Run `gpt-oss-20b`](#run-gpt-oss-20b)
  - [The two ways to use uv on Pegasus](#the-two-ways-to-use-uv-on-pegasus)
    - [Single package srun](#single-package-srun)
    - [Full project srun](#full-project-srun)
  - [All-in-one run script](#all-in-one-run-script)
    - [Prerequisites](#prerequisites-1)
    - [Usage](#usage)
    - [The alternative](#the-alternative)

## Quickstart

### Prerequisites

based on: [DFKI-NLP/vLLM-Starter#2 (comment)](https://github.com/DFKI-NLP/vLLM-Starter/issues/2#issuecomment-3383218249)

1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
1. open a new shell (or a create a new screen: `screen -S vLLM-Starter`)

### Run `gpt-oss-20b`

Based on instructions from https://github.com/DFKI-NLP/vLLM-Starter.

start the service:

```bash
export HF_HOME="/netscratch/$USER/cache/hf"
export VLLM_CACHE_ROOT="/netscratch/$USER/cache/vllm"
srun --partition=RTXA6000-SLT \
     --job-name=vllm_serve \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --time=0-04:00:00 \
     uvx --cache-dir /netscratch/$USER/cache/uv \
         vllm@0.12.0 serve "openai/gpt-oss-20b" \
             --download-dir=/ds/models/llms/cache \
             --port=18000
```

If you need a different version of vLLM, change `@0.12.0` to `@your.version.here` or `@latest`. [docs](https://docs.astral.sh/uv/guides/tools/#requesting-specific-versions)

Note: This may take some time, wait for `Application startup complete.`

**Important**: For models other than gpt-oss-20B, please check the respective configs in configs/extractor/llm for
additional command line arguments to vllm serve. For example, Qwen3 requires to specify the additional argument
'--reasoning-parser deepseek_r1', Nemotron-Nano uses '--trust-remote-code' etc.

query:

```bash
# Note: You may need to select a different NODE than `serv-9220`. I got it by calling `squeue -u $USER`.
curl http://serv-9220.kl.dfki.de:18000/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "openai/gpt-oss-20b",
        "prompt": "San Francisco is a",
        "max_tokens": 7,
        "temperature": 0
    }'
```

result:

```bash
{
   "id":"cmpl-daceb4b0e6cf49338a588eff564ad85a",
   "object":"text_completion",
   "created":1759957476,
   "model":"openai/gpt-oss-20b",
   "choices":[
      {
         "index":0,
         "text":" city in California, USA. It",
         "logprobs":null,
         "finish_reason":"length",
         "stop_reason":null,
         "token_ids":null,
         "prompt_logprobs":null,
         "prompt_token_ids":null
      }
   ],
   "service_tier":null,
   "system_fingerprint":null,
   "usage":{
      "prompt_tokens":4,
      "total_tokens":11,
      "completion_tokens":7,
      "prompt_tokens_details":null
   },
   "kv_transfer_params":null
}
```

## The two ways to use uv on Pegasus

In General:

- In case you want to run a gated model, log into HuggingFace and make sure you have the correct access permissions.
- Choose model, resources and max job runtime carefully.
- Check for special requirements, like chat templates, tokenisers, and allowing local code execution.

### Single package srun

If you want to do not much setup and all you need is one package, for example when using `vllm serve`, use `uvx` with the following flag and eviroment variables:

- `export HF_HOME="/netscratch/$USER/cache/hf"` this prevents the huggingface cache from filling up your home directory.
- `export VLLM_CACHE_ROOT="/netscratch/$USER/cache/vllm"` this prevents the vLLM cache from filling up your home directory.
- `--cache-dir /netscratch/$USER/cache/uv` this prevents uv from filling up your home directory.

This approach is used in the [Quickstart](#quickstart) section.

If the tool you want to use is invoked with a different name than it is installed, then use `--from <install-name>`. <br>
example:
`uvx --from rust-just just` The `rust-just` package is invoked by calling `just`.

### Full project srun

To run a uv project with any number of custom python packages in your environment, you need to set up a few things.

Firstly, you need to create directories on netscratch where the uv virtual environment and caches can live:

```bash
mkdir -p /netscratch/$USER/cache/uv
mkdir -p /netscratch/$USER/cache/uv-venvs
mkdir -p /netscratch/$USER/cache/hf
mkdir -p /netscratch/$USER/cache/vllm
```

Secondly, you need to set the environment variables for the uv cache and virtual environment to the directories you just created. This will point uv there and prevent it from causing your home directory to overflow.

```bash
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"
export UV_PROJECT_ENVIRONMENT="/netscratch/$USER/cache/uv-venvs/kibad-llm"
```

Thirdly, create the virtual environment and symlink the directories so that you don't need to set the environment variables each time you open a new shell.

```bash
# create the .venv
uv sync
# link the .venv
ln -s /netscratch/$USER/cache/uv-venvs/kibad-llm ./.venv
# link the caches
ln -s /netscratch/$USER/cache/uv ~/.cache/uv
ln -s /netscratch/$USER/cache/hf ~/.cache/huggingface
ln -s /netscratch/$USER/cache/vllm ~/.cache/vllm
```

Now you can all of your python code without worrying about the uv cache, virtual environment, or huggingface/ vllm caches.

```bash
srun --your-srun-flag \
     uv run -m your.file.here
```

**Important**: When running experiments for KIBA-D, it is highly (!) recommended to sym-link output directories
to the folders in `/netscratch/hennig/kiba-d/`, to ensure that everyone has access to the experiment results. Consider
executing the following on a fresh clone of the `kibad-llm` repository:

```bash
ln -s /netscratch/hennig/kiba-d/logs ./logs
ln -s /netscratch/hennig/kiba-d/predictions ./predictions
```

(If these folders already exist in your kibad-llm repository because you ran inference previously, you might want to
delete or rename them, and then execute the above commands.)

## All-in-one run script for 'in_process' VLLM configs

To host an llm on the cluster and run uv code against it in a python-internal setup, without the use of an external
VLLM server, use the all-in-one run script `run_in_process.sh`. Note that this requires the use of the `*_in_process.yaml` configs
in `configs/extractor/llm` when executing `uv run -m kibad_llm.predict`.

### Prerequisites

In order to use `run_in_process.sh` you need to have followed the steps in [Full project srun](#full-project-srun)!

In addition, set up your `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and fill out the following mandatory variables:

```bash
HF_TOKEN=<your_hf_token>
OPENAI_API_KEY=<your_openai_api_key>
VLLM_DOWNLOAD_DIR=/ds/models/llms/cache
```

You can create an Open AI key at https://platform.openai.com/api-keys and Huggingface access tokens at https://huggingface.co/settings/tokens.

### Usage

`run_in_process.sh` uses flags with command line arguments.

- `-h | --help` displays very similar help to this.

- `pa | --partition` is the slurm partition to submit the job to. This is an optional flag and uses `"RTX6000-SLT"` per default.

- `-t | --time` is the maximum time the slurm job is allowed to run. This is an optional flag and uses one hour per default.

- `-u | --uv` is used for all `uv run` arguments. If there are multiple, make sure to wrap them in quotes like `"-m some.code"` which results in `uv run -m some.code`. This is a required flag.

The script takes care of everything start to finish and executes all code on the compute node. As soon as the job gets resources, the uv run command (e.g. `predict.py`) starts.

### The alternatives

## All-in-one run 'external VLLM' script

To host an llm on the cluster and run uv code against it as soon as the model is ready, use the all-in-one run script `run_with_llm.sh`

### Prerequisites

In order to use `run_with_llm.sh` you need to have followed the steps in [Full project srun](#full-project-srun)!

### Usage

`run_with_llm.sh` uses flags with command line arguments.

- `-h | --help` displays very similar help to this.

- `-v | --vllm` is used for almost all arguments relevant to vLLM. If there are multiple, make sure to wrap them in quotes like `"some/mistral --trust-remote-code"`. This is a required flag.

- `-vv | --vllm-version` is the vLLM version to run. This is an optional flag and uses version 0.12.0 per default.

- `-po | --port` is the port vLLM and the uv code communicate on. This is an optional flag and uses a random port per default.

- `pa | --partition` is the slurm partition to submit the job to. This is an optional flag and uses `"RTX6000-SLT"` per default.

- `-t | --time` is the maximum time the slurm job is allowed to run. This is an optional flag and uses one hour per default.

- `-u | --uv` is used for all `uv run` arguments. If there are multiple, make sure to wrap them in quotes like `"-m some.code"` which results in `uv run -m some.code`. This is a required flag.

The script takes care of everything start to finish and executes all code on the compute node. As soon as the job gets resources, vLLM starts. The script then waits till vLLm is ready and starts your code with uv right after. This allows you to run heavy jobs without straining the login node. You can cancel the job with `ctrl-c` or `scancel` any time and don't need to worry about residual processes.

### Run with VLLM but on Login Node

`run_with_llm_login_node_exec.sh` is very similar to `run_with_llm.sh`. The main difference is that this script puts vLLM on the compute node and runs your uv code locally on the login node. You need to be careful when using this script because of the strain you put on the login node.
Depending on how your uv code fails or the script is cancelled, the slurm job may need to be cancelled separately.
This script may make working on your code easier, depending on your needs, but you should probably have a quick look at how the script works in that case.
