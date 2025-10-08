# Title
**TODO**

## Models

### API

- OpenAI
- Mistral/Mistral-Nemo
- Gemini
- Claude

### Self-hosted

```bash 
    # set variables
    export HF_HOME="/netscratch/$USER/.cache/hf"
    export HF_HUB_CACHE="/netscratch/$USER/.cache/hf-models" 
    PORT=18535  # arbitrary number between 10000 and 65536
    MODEL_PARAMS=""
    PARTITION="RTXA6000"

    echo "============================================="
    echo ">>> USING PARTITION $PARTITION"
    echo ">>> WITH MODEL $MODEL_PARAMS"
    echo ">>> RUNNING ON PORT $PORT"
    echo "============================================="

    srun --partition=$PARTITION \
         --job-name=kiba-d_vllm_serve \
         --nodes=1 \
         --ntasks=1 \
         --cpus-per-task=6 \
         --gpus-per-task=1 \
         --mem-per-cpu=4G \
         --oversubscribe \
         --time=1-00:00:00 \
         vllm serve $MODEL_PARAMS \
                    --port=$PORT
```

- Olmo 2
- Llama3.X
- Teuken 7B
  - `MODEL_PARAMS="openGPT-X/Teuken-7B-instruct-commercial-v0.4 --trust-remote-code --chat-template=./models/chat-templates/teuken.jinja"`
  - Teuken requires a custom chat template to allow for system prompts
- DeepSeek
- GPT-OSS
  - `MODEL_PARAMS="openai/gpt-oss-20b"`
- Mistral/Mistral-Nemo
- Extract-0
