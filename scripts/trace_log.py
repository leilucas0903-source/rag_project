import argparse
import sys
from pathlib import Path

def trace_request(log_path: str, request_id: str):
    """
    按 request_id 筛选日志行
    """
    log_file = Path(log_path)
    if not log_file.exists():
        print(f"❌ 错误: 日志文件未找到: {log_path}")
        return

    print(f"🔍 正在追踪 Request ID: [{request_id}] ...\n" + "-"*50)
    
    found_count = 0
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 假设日志格式中包含了 request_id
                if request_id in line:
                    print(line.strip())
                    found_count += 1
        
        if found_count == 0:
            print(f"⚠️ 未找到关联该 ID 的日志条目，请确认 ID 是否正确或日志路径是否匹配。")
        else:
            print("-"*50 + f"\n✅ 扫描结束，共找到 {found_count} 条相关日志。")
            
    except Exception as e:
        print(f"❌ 读取日志时发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 Request ID 快速定位日志")
    parser.add_argument("req_id", help="需要查询的 request_id")
    parser.add_argument("--file", default="logs/app.log", help="日志文件路径 (默认: logs/app.log)")
    
    args = parser.parse_args()
    trace_request(args.file, args.req_id)