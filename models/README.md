# How-To Run an LLM on the DFKI Cluster

- [Quickstart](#quickstart)
  - [Prerequisites](#prerequisites)
  - [Run `gpt-oss-20b`](#run-gpt-oss-20b)
- [uv and Pegasus, the DFKI Cluster](#uv-and-pegasus-the-dfki-cluster)
  - ["I just need one package"](#i-just-need-one-package)
  - [Set `UV_PROJECT_ENVIRONMENT`](#set-uv_project_environment)
  - [Symlink .venv](#symlink-venv)

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
     uv run --with vllm --cache-dir /netscratch/$USER/cache/uv \
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

## uv and Pegasus, the DFKI Cluster

For running your code on Pegasus, you have three options.

### "I just need one package"

If all you need is one package, for example when using `vllm serve`, it is recommended to use the `-w your-package` option with a cache on netscratch.

```bash
# first create a cache directory on netscratch
mkdir -p /netscratch/$USER/cache/uv
# run the command with the package and cache
srun --partition=RTXA6000-SLT \
     --job-name=vllm_serve \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --time=1-00:00:00 \
     uv run -w vllm --cache-dir /netscratch/$USER/cache/uv \
            vllm serve "openai/gpt-oss-20b" \
                       --download-dir=/ds/models/llms/cache \
                       --port=18000
```

Alternatively, the cache directory can be set as an environment variable:

```bash
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"
```

### Set `UV_PROJECT_ENVIRONMENT`

Set up the directory once:

```bash
mkdir -p /netscratch/$USER/cache/uv
mkdir -p /netscratch/$USER/cache/uv-venvs
```

Then set the environment variables for every new shell session:

```bash
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"
export UV_PROJECT_ENVIRONMENT="/netscratch/$USER/cache/uv-venvs/kibad-llm"
```

Using this setup, you run your scripts like you would do locally, except they're prefixed by srun.

```bash
srun --partition=RTXA6000-SLT \
     --job-name=vllm_serve \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --time=1-00:00:00 \
     uv run -m your.file.here
```

For more info on the project environment path, please refer to the [docs](https://docs.astral.sh/uv/concepts/projects/config/#project-environment-path).

### Symlink .venv

First follow the steps outlined in the above section [Set `UV_PROJECT_ENVIRONMENT`](#set-uv_project_environment). <br>
Then run `uv sync` to ensure that all directories are created properly.
Lastly, create both symlinks.

```bash
# link the .venv
ln -s /netscratch/$USER/cache/uv-venvs/kibad-llm ./.venv
# link the cache
ln -s /netscratch/$USER/cache/uv ~/.cache/uv
```

Now you do not need to add the environment variables each time you start up a new shell session. <br>
Running your scripts works the same way as described in the above section [Set `UV_PROJECT_ENVIRONMENT`](#set-uv_project_environment).
