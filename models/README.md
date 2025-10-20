# How-To Run an LLM on the DFKI Cluster

- [How-To Run an LLM on the DFKI Cluster](#how-to-run-an-llm-on-the-dfki-cluster)
  - [Quickstart](#quickstart)
    - [Prerequisites](#prerequisites)
    - [Run `gpt-oss-20b`](#run-gpt-oss-20b)
  - [The two ways to use uv on Pegasus](#the-two-ways-to-use-uv-on-pegasus)
    - [Single package srun](#single-package-srun)
    - [Full project srun](#full-project-srun)

## Quickstart

### Prerequisites

based on: [DFKI-NLP/vLLM-Starter#2 (comment)](https://github.com/DFKI-NLP/vLLM-Starter/issues/2#issuecomment-3383218249)

1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
1. create uv cache dir on netscratch: `mkdir -p /netscratch/$USER/cache/uv`
1. open a new shell (or a create a new screen: `screen -S vLLM-Starter`)

### Run `gpt-oss-20b`

Based on instructions from https://github.com/DFKI-NLP/vLLM-Starter.

start the service:

```bash
srun --partition=RTXA6000-SLT \
     --job-name=vllm_serve \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --time=1-00:00:00 \
     uv run --w vllm --cache-dir /netscratch/$USER/cache/uv \
            vllm serve "openai/gpt-oss-20b" \
                       --download-dir=/ds/models/llms/cache \
                       --port=18000
```

Note: This may take some time, wait for `Application startup complete.`

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

If you want to do not much setup and all you need is one package, for example when using `vllm serve`, use `uv run` with these two flags:

- `-w your-package` this could be vllm or whatever other package you need.
- `--cache-dir /netscratch/$USER/cache/uv` this prevents uv from filling up your home directory. It does however require you to set up the cache dir `mkdir -p /netscratch/$USER/cache/uv`.

This approach is used in the [Quickstart](#quickstart) section.

### Full project srun

To run a uv project with any number of custom python packages in your environment, you need to set up a few things.

Firstly, you need to create directories on netscratch where the uv cache and virtual environment can live:

```bash
mkdir -p /netscratch/$USER/cache/uv
mkdir -p /netscratch/$USER/cache/uv-venvs
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
# link the cache
ln -s /netscratch/$USER/cache/uv ~/.cache/uv
```

Now you can all of your python code without worrying about the uv cache or virtual environment.

```bash
srun --your-srun-flag \
     uv run -m your.file.here
```
