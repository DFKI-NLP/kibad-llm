# How-To Run an LLM on the DFKI Cluster
## Prerequisites

based on: [DFKI-NLP/vLLM-Starter#2 (comment)](https://github.com/DFKI-NLP/vLLM-Starter/issues/2#issuecomment-3383218249)

    Install uv: https://docs.astral.sh/uv/getting-started/installation/
    create uv cache dir on netscratch: mkdir -p /netscratch/$USER/cache/uv
    open a new shell (or a create a new screen: screen -S vLLM-Starter)

## Run `gpt-oss-20b`

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
# Note: You may select a different NODE than `serv-9220`. I got it by calling `squeue -u $USER`.
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
