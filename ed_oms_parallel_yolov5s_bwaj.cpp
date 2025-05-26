#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <random>
#include <cstring>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstdlib>
#include <vector>
#include <mutex>
#include <queue>
#include <condition_variable>
#include <atomic>
#include <cstdio>
#include <sys/stat.h>
#include <unordered_map>
#include <algorithm>

const char* EC_IP   = "192.168.0.100";
const int   PORT    = 5000;
const char* IMAGE   = "000000006321.jpg";
const char* PY_CMD  = "python3 yolov5/yolov5s_EC_bwaj.py";

std::mutex stats_mutex;
int completed_tasks    = 0;
int ran_on_ed          = 0;
int sent_to_ec         = 0;
long total_latency_ms  = 0;

std::mutex queue_mutex;
std::condition_variable queue_cv;
std::queue<std::string> local_queue;
bool stop_local = false;

std::unordered_map<int, long> local_task_start_ms;
std::unordered_map<int, long> local_task_end_ms;
std::mutex time_map_mutex;

void log_result(const std::string& entry) {
    std::lock_guard<std::mutex> lock(stats_mutex);
    std::ofstream log("ed_task_log.txt", std::ios::app);
    log << entry << std::endl;
}

FILE* start_python_helper(int duration_sec) {
    std::string py_cmd = std::string(PY_CMD) + " " + std::to_string(duration_sec);
    FILE* py = popen(py_cmd.c_str(), "w");
    if (!py) {
        std::cerr << "[ED] Failed to launch python fallback\n";
        exit(1);
    }
    return py;
}

void enqueue_local_run(int token_ed) {
    std::string task_info = std::to_string(token_ed) + ":" + IMAGE;
    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        local_queue.push(task_info);
    }
    {
        std::lock_guard<std::mutex> lock(time_map_mutex);
        long start_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        local_task_start_ms[token_ed] = start_ms;
    }
    queue_cv.notify_one();
}

void local_run_dispatch(FILE* py) {
    while (true) {
        std::unique_lock<std::mutex> lock(queue_mutex);
        queue_cv.wait(lock, [] { return !local_queue.empty() || stop_local; });
        if (stop_local && local_queue.empty()) break;
        std::string task = local_queue.front();
        local_queue.pop();
        lock.unlock();
        fprintf(py, "%s\n", task.c_str());
        fflush(py);
    }
}

void start_done_listener() {
    const char* fifo_path = "fallback_notify.fifo";
    mkfifo(fifo_path, 0666);
    FILE* fifo = fopen(fifo_path, "r");
    if (!fifo) {
        std::cerr << "[ED] Cannot open fallback_notify.fifo\n";
        return;
    }
    char buffer[512];
    while (fgets(buffer, sizeof(buffer), fifo)) {
        std::string line(buffer);
        line.erase(std::remove(line.begin(), line.end(), '\n'), line.end());
        auto first = line.find(',');
        auto second = line.find(',', first + 1);
        if (first == std::string::npos || second == std::string::npos) continue;
        int token = std::stoi(line.substr(0, first));
        long done_time = std::stol(line.substr(second + 1));
        {
            std::lock_guard<std::mutex> lock(time_map_mutex);
            local_task_end_ms[token] = done_time;
        }
        log_result("[ED_DONE] token_ed=" + std::to_string(token));
    }
    fclose(fifo);
}

void run_request(int token_ed) {
    auto start = std::chrono::high_resolution_clock::now();
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        enqueue_local_run(token_ed);
        return;
    }
    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    inet_pton(AF_INET, EC_IP, &serv_addr.sin_addr);
    if (connect(sock, (sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        close(sock);
        enqueue_local_run(token_ed);
        return;
    }
    std::string req = "REQ:" + std::to_string(token_ed) + ":yolov5s:PI5";
    send(sock, req.c_str(), req.size(), 0);
    char buf[256] = {0};
    int received = recv(sock, buf, sizeof(buf) - 1, 0);
    if (received <= 0) {
        close(sock);
        enqueue_local_run(token_ed);
        return;
    }
    std::string response(buf, received);
    if (response.rfind("GRANT:", 0) == 0) {
        std::string token_ec = response.substr(6);
        std::string ok_msg = "OK:" + token_ec + ":" + std::to_string(token_ed);
        send(sock, ok_msg.c_str(), ok_msg.size(), 0);
        std::ifstream file(IMAGE, std::ios::binary);
        if (!file) {
            close(sock);
            return;
        }
        char img_buf[4096];
        while (file.read(img_buf, sizeof(img_buf)))
            send(sock, img_buf, file.gcount(), 0);
        if (file.gcount() > 0)
            send(sock, img_buf, file.gcount(), 0);
        file.close();
        shutdown(sock, SHUT_WR);
        char done_buf[16] = {0};
        recv(sock, done_buf, sizeof(done_buf) - 1, 0);
        auto end = std::chrono::high_resolution_clock::now();
        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            sent_to_ec++;
        }
    } else {
        enqueue_local_run(token_ed);
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            ran_on_ed++;
        }
    }
    close(sock);
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: ./ed_oms_yolov5s <lambda_rate> <duration_sec>\n";
        return 1;
    }
    double lambda_rate = std::stod(argv[1]);
    int duration_sec = std::stoi(argv[2]);

    FILE* py = start_python_helper(duration_sec);
    std::thread py_thread(local_run_dispatch, py);
    std::thread listener_thread(start_done_listener);

    std::atomic<int> total_generated{0};
    std::atomic<bool> all_generated{false};

    std::queue<int> task_queue;
    std::mutex task_queue_mutex;
    std::condition_variable task_queue_cv;

    auto program_start = std::chrono::high_resolution_clock::now();

    std::thread generator([&]() {
        std::mt19937 gen(std::random_device{}());
        std::exponential_distribution<double> dist(lambda_rate);
        int token = 0;
        auto start = std::chrono::steady_clock::now();
        while (true) {
            auto now = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::seconds>(now - start).count() >= duration_sec) break;

            {
                std::lock_guard<std::mutex> lock(task_queue_mutex);
                task_queue.push(token);
            }
            total_generated++;
            task_queue_cv.notify_one();
            std::this_thread::sleep_for(std::chrono::duration<double>(dist(gen)));
            token++;
        }
        all_generated = true;
        task_queue_cv.notify_all();
    });

    const int POOL_SIZE = 32;
    std::vector<std::thread> workers;
    for (int i = 0; i < POOL_SIZE; ++i) {
        workers.emplace_back([&]() {
            while (true) {
                int token = -1;
                {
                    std::unique_lock<std::mutex> lock(task_queue_mutex);
                    task_queue_cv.wait(lock, [&]() { return !task_queue.empty() || all_generated; });
                    if (task_queue.empty() && all_generated) return;
                    token = task_queue.front();
                    task_queue.pop();
                }
                run_request(token);
            }
        });
    }

    generator.join();
    for (auto& w : workers) w.join();
    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        stop_local = true;
    }
    queue_cv.notify_all();
    py_thread.join();
    pclose(py);
    listener_thread.join();

    long corrected_latency = total_latency_ms;
    {
        std::lock_guard<std::mutex> lock(time_map_mutex);
        for (auto& kv : local_task_end_ms) {
            int t = kv.first;
            if (local_task_start_ms.count(t)) {
                corrected_latency += (kv.second - local_task_start_ms[t]);
            }
        }
    }

    auto program_end = std::chrono::high_resolution_clock::now();
    long total_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(program_end - program_start).count();

    std::cout << "\n===== FINAL STATS =====\n";
    std::cout << "Total tasks generated:   " << total_generated << "\n";
    std::cout << "Total execution time:    " << total_time_ms << " ms\n";
    std::cout << "Total tasks completed:   " << completed_tasks << "\n";
    std::cout << "Tasks sent to EC:        " << sent_to_ec << "\n";
    std::cout << "Tasks run locally:       " << ran_on_ed << "\n";
    double pct_ed = completed_tasks ? (100.0 * ran_on_ed / completed_tasks) : 0.0;
    double pct_ec = completed_tasks ? (100.0 * sent_to_ec / completed_tasks) : 0.0;
    std::cout << "Percent local (ED):      " << pct_ed << " %\n";
    std::cout << "Percent offloaded (EC):  " << pct_ec << " %\n";
    long avg_latency = completed_tasks ? (corrected_latency / completed_tasks) : 0;
    std::cout << "Avg latency per task:    " << avg_latency << " ms\n";
    std::cout << "=========================" << std::endl;

    return 0;
}
