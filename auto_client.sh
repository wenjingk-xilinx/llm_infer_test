

PARAMS_LIST=(
#"--max_input_len 1000 --min_input_len 800 --max_output_len 500 --min_output_len 300 --concurrency 14"
#"--max_input_len 2000 --min_input_len 1600 --max_output_len 500 --min_output_len 300 --concurrency 10"
#"--max_input_len 3600 --min_input_len 3000 --max_output_len 500 --min_output_len 300 --concurrency 6"
#"--max_input_len 20000 --min_input_len 16000 --max_output_len 500 --min_output_len 300 --concurrency 1"
#"--max_input_len 1000 --min_input_len 800 --max_output_len 2000 --min_output_len 1600 --concurrency 18"
#"--max_input_len 200 --min_input_len 100 --max_output_len 4000 --min_output_len 3600 --concurrency 18"
"--max_input_len 4400 --min_input_len 3600 --max_output_len 2200 --min_output_len 1800 --concurrency 10"
)

#timestamp=$(date +"%Y%m%d_%H%M")
MODEL_PATH="/mnt/raid0/wenjingk/DeepSeek-R1"
LOG_DIR="/mnt/raid0/wenjingk/vllm_deepseekr1/0331/log_docker0331_dsv3_perf_mla1"
for PARAMS in "${PARAMS_LIST[@]}"; do

python3 auto_adjust_concurrency.py \
    --model_path "$MODEL_PATH" \
    --log_dir "$LOG_DIR" \
    $PARAMS --query_multiplier 10


echo "----------------------------------------"

done
