import subprocess
import re
import os
import time
import argparse
from typing import Dict, Optional
import shutil

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="自动调整并发度以优化解码时间")
    parser.add_argument("--model_path", type=str, required=True, help="模型路径")
    parser.add_argument("--log_dir", type=str, required=True, help="日志存储目录")
    parser.add_argument("--concurrency", type=int, default=16, help="初始并发度")
    parser.add_argument("--query_multiplier", type=int, default=10)
    parser.add_argument("--max_retries", type=int, default=10, help="最大调整次数")
    parser.add_argument("--target_decode_time", type=int, default=50, help="目标解码时间 (ms)")
    parser.add_argument("--tolerance", type=int, default=1, help="允许的误差范围 (ms)")
    
    # 基准测试参数
    parser.add_argument("--max_input_len", type=int, required=True, help="最大输入长度")
    parser.add_argument("--min_input_len", type=int, required=True, help="最小输入长度")
    parser.add_argument("--max_output_len", type=int, required=True, help="最大输出长度")
    parser.add_argument("--min_output_len", type=int, required=True, help="最小输出长度")

    return parser.parse_args()

def run_benchmark(model_path: str, params: Dict[str, str], log_file: str) -> None:
    """运行基准测试"""
    query_num = int(params["--concurrency"]) * 10
    cmd = [
        "./kunlun-benchmark", "vllm", "server",
        "--port", "8000",
        "--prompt_type", "normal_distribution",
        "--model_area", "llm",
        "--dev_name", "AMD308x",
        "--work_mode", "manual",
        "--model_path", model_path,
        "--query_num", str(query_num),
        *[item for pair in params.items() for item in pair],  # 展开参数
    ]

    print(f"\n🚀 Running benchmark with concurrency = {params['--concurrency']}")
    print("Command:", " ".join(cmd))

    with open(log_file, "w") as f:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="")  # 实时输出日志
            f.write(line)

def extract_decode_time(log_file: str) -> Optional[float]:
    """从日志文件中提取 `Average Decode Time`"""
    try:
        with open(log_file, "r") as f:
            content = f.read()
        match = re.search(r"Average\s+Decode\s+Time\s+\(TPOT\)\s*\|\s*([0-9.]+)\s*ms", content)
        return float(match.group(1)) if match else None
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return None

def main():
    args = parse_args()
    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(f"{args.log_dir}/attempts", exist_ok=True)
    os.makedirs(f"{args.log_dir}/final", exist_ok=True)

    base_params = {
        "--max_input_len": str(args.max_input_len),
        "--min_input_len": str(args.min_input_len),
        "--max_output_len": str(args.max_output_len),
        "--min_output_len": str(args.min_output_len),
        "--query_num":str(args.concurrency*args.query_multiplier),
        "--concurrency": str(args.concurrency),
    }

    current_concurrency = args.concurrency
    retry_count = 0
    last_decode_time = None
    best_concurrency = None
    best_decode_time = float('inf')
    best_attempt_log = None
    while retry_count < args.max_retries:
        retry_count += 1
        print(f"\n📊 Attempt {retry_count}/{args.max_retries}")

        # 更新并发度
        base_params["--concurrency"] = str(current_concurrency)
        base_params["--query_num"] = str(current_concurrency*args.query_multiplier)
        log_suffix = "_".join([f"{k.lstrip('-')}_{v}" for k, v in base_params.items()])
        attempt_log = f"{args.log_dir}/attempts/{log_suffix}_attempt_{retry_count}.log"

        # 运行测试
        if not last_decode_time:
            run_benchmark(args.model_path, base_params, attempt_log+"warmup")
        run_benchmark(args.model_path, base_params, attempt_log)
        #log_file="/mnt/raid0/wenjingk/vllm_deepseekr1/0331/log_docker0325_dsv3_perf2/max_input_len_1000_min_input_len_800_max_output_len_2000_min_output_len_1600_concurrency_20.log"
        decode_time = extract_decode_time(attempt_log)

        if decode_time is None:
            print("⚠️ Skipping due to log parsing error.")
            continue

        print(f"⏱️ Current Decode Time: {decode_time} ms (Target: {args.target_decode_time} ± {args.tolerance} ms)")

        # 调整策略
        if (args.target_decode_time - args.tolerance) <= decode_time <= (args.target_decode_time + args.tolerance):
            print(f"✅ Success! Optimal concurrency = {current_concurrency} (Decode Time = {decode_time} ms)")
            best_attempt_log = attempt_log
            break
        elif last_decode_time and last_decode_time > args.target_decode_time and decode_time < (args.target_decode_time - args.tolerance):
            print(f"🛑 Stopping: Last decode time was too high ({last_decode_time} > {args.target_decode_time}), now too low ({decode_time} < {args.target_decode_time - args.tolerance})")
            best_attempt_log = attempt_log
            break
        elif last_decode_time and last_decode_time < (args.target_decode_time - args.tolerance) and decode_time > (args.target_decode_time + args.tolerance):
            print(f"🛑 Stopping: Last decode time was too low ({last_decode_time} < {args.target_decode_time - args.tolerance}), now too high ({decode_time} > {args.target_decode_time + args.tolerance})")
            best_attempt_log = last_attempt_log
            break
        elif decode_time > args.target_decode_time :
            if current_concurrency<2:
                print(f"🔻 Decode Time too high ({decode_time} > {args.target_decode_time}). Concurrency<2, cannot be smaller!")
                best_attempt_log = attempt_log
                break
            new_concurrency = max(current_concurrency - 2, 1)
            print(f"🔻 Decode Time too high ({decode_time} > {args.target_decode_time}). Decreasing concurrency to {new_concurrency}")
        else:
            new_concurrency = current_concurrency + 2
            print(f"🔺 Decode Time too low ({decode_time} < {args.target_decode_time}). Increasing concurrency to {new_concurrency}")

        last_decode_time = decode_time
        last_attempt_log = attempt_log
        current_concurrency = new_concurrency
        time.sleep(1)

    else:
        print(f"⚠️ Reached max retries ({args.max_retries}). Final concurrency = {current_concurrency}")

    if not best_attempt_log:
        best_attempt_log = last_attempt_log

    shutil.copy(best_attempt_log, f"{args.log_dir}/final/{log_suffix}.log")
#    with open(f"{args.log_dir}/best_params.txt", "w") as f:
#        f.write(f"Best Concurrency: {best_concurrency}\n")
#        f.write(f"Best Decode Time: {best_decode_time} ms\n")

    print(f"\n🎯 Final Result: {best_attempt_log}")
    #print(f"\n🎯 Final Result: Best Concurrency = {best_concurrency}, Decode Time = {best_decode_time} ms")

if __name__ == "__main__":
    main()
