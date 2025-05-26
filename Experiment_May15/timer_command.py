import sys
import subprocess
import time

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 timer.py <command> [args...]")
        sys.exit(1)

    cmd = sys.argv[1:]

    start = time.perf_counter_ns()
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    end = time.perf_counter_ns()

    elapsed_us = (end - start) / 1000  
    elapsed_ms = elapsed_us / 1000        

    print(f"Time taken: {elapsed_ms:.4f} ms")  

if __name__ == "__main__":
    main()
