# llm_infer_test （Auto-Concurrency Tuner for Kunlun-Benchmark）
## Overview
Automated script that dynamically adjusts concurrency to optimize decode time performance in Kunlun-Benchmark tests.

## Quick Start
```bash
python auto_adjust_concurrency.py \
    --model_path <model_path> \
    --log_dir <log_directory> \
    --max_input_len <value> \
    --min_input_len <value> \
    --max_output_len <value> \
    --min_output_len <value>
```
Example wrapper: ./auto_client.sh

## Key Features
- Auto-tunes concurrency to reach target decode time (default: 50ms)
- Stores logs in organized directory structure:

  Attempt logs: $log_dir/attempts/

  Final best result: $log_dir/final/
- Configurable initial concurrency and adjustment parameters

