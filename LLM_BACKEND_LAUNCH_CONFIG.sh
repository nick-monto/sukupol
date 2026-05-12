#!/usr/bin/env bash
./build/bin/llama-server \
  -hf unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_M \
  --fit on \
  -c 64000 \
  -np 1 \
  --n-cpu-moe 20 \
  --no-mmap \
  --no-mmproj \
  -fa on \
  -ctk q8_0 \
  -ctv turbo4 \
  --checkpoint-every-n-tokens 2048 \
  --ctx-checkpoints 64 \
  --temp 1.0 --top-p 0.95 --top-k 20 \
  --min-p 0.0 --presence-penalty 1.5 --repeat-penalty 1.0 \
  --reasoning-budget -1 \
  --host 0.0.0.0 \
  --port 8033