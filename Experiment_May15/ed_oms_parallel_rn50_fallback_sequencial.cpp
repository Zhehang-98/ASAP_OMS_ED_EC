// ed_oms.cpp
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
#include <sys/resource.h>
#include <sys/stat.h>
#include <unordered_map>
#include <algorithm>

// =========================== CONFIGURATION =========================================
const char* EC_IP   = "192.168.0.100";
const int   PORT    = 5000;
const char* IMAGE   = "COCO_test_1220/000000006321.jpg";
const char* PY_CMD  = "python3 rn50_local_run_serial_measure.py";

// =========================== GLOBAL STATE =========================================
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

// =================== PYTHON FALLBACK PROCESS COMMUNICATION ========================
FILE* start_python_helper() {
    FILE* py = popen(PY_CMD, "w");
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

// ====================== LISTEN FOR PYTHON DONE NOTIFICATIONS ======================
void start_done_listener() {
    const char* fifo_path = "/tmp/fallback_notify.fifo";
    mkfifo(fifo_path, 0666);

    FILE* fifo = fopen(fifo_path, "r");
    if (!fifo) {
        std::cerr << "[ED] Failed to open fallback_notify.fifo for reading\n";
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
        std::string infer_time_str = line.substr(first + 1, second - first - 1);
        long done_time = std::stol(line.substr(second + 1));

        {
            std::lock_guard<std::mutex> lock(time_map_mutex);
            local_task_end_ms[token] = done_time;
        }

        log_result("[ED_DONE] token_ed=" + std::to_string(token)
                   + " latency=" + infer_time_str
                   + " ms done_time=" + std::to_string(done_time));
    }

    fclose(fifo);
}

// ============================ EC TASK REQUEST =====================================
void run_request(int token_ed) {
    auto start = std::chrono::high_resolution_clock::now();
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("[ED] socket() failed");
        enqueue_local_run(token_ed);
        return;
    }

    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    inet_pton(AF_INET, EC_IP, &serv_addr.sin_addr);

    if (connect(sock, (sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("[ED] connect() failed");
        close(sock);
        enqueue_local_run(token_ed);
        return;
    }

    std::string req = "REQ:" + std::to_string(token_ed) + ":resnet_50:PI5";
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
        int bytes = recv(sock, done_buf, sizeof(done_buf) - 1, 0);
        if (bytes <= 0) {
            close(sock);
            return;
        }

        auto end = std::chrono::high_resolution_clock::now();
        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            sent_to_ec++;
        }

        log_result("[ED_SENT] token_ed=" + std::to_string(token_ed)
                   + " token_ec=" + token_ec
                   + " duration=" + std::to_string(duration) + " ms");
    } else if (response == "DROP") {
        enqueue_local_run(token_ed);
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            ran_on_ed++;
        }
        log_result("[ED_FALLBACK] token_ed=" + std::to_string(token_ed) + " fallback initiated");
    }

    close(sock);
}

// ========================== MAIN EXECUTION CONTROL ===============================
std::queue<int> task_queue;
std::mutex task_queue_mutex;
std::condition_variable task_queue_cv;
std::atomic<bool> all_generated{false};

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: ./ed_oms <tasks_per_second> <num_tasks>\n";
        return 1;
    }

    int tasks_per_second = std::stoi(argv[1]);
    int total_requests   = std::stoi(argv[2]);
    int interval_ms      = 1000 / tasks_per_second;

    FILE* py = start_python_helper();
    std::thread py_thread(local_run_dispatch, py);
    std::thread done_listener_thread(start_done_listener);

    const int thread_pool_size = 32;

    std::thread generator_thread([&]() {
        for (int i = 0; i < total_requests; ++i) {
            {
                std::lock_guard<std::mutex> lock(task_queue_mutex);
                task_queue.push(i);
            }
            task_queue_cv.notify_one();
            std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
        }
        all_generated = true;
        task_queue_cv.notify_all();
    });

    std::vector<std::thread> workers;
    for (int i = 0; i < thread_pool_size; ++i) {
        workers.emplace_back([&]() {
            while (true) {
                int token = -1;
                {
                    std::unique_lock<std::mutex> lock(task_queue_mutex);
                    task_queue_cv.wait(lock, [] {
                        return !task_queue.empty() || all_generated;
                    });
                    if (task_queue.empty() && all_generated) return;
                    token = task_queue.front();
                    task_queue.pop();
                }
                run_request(token);
            }
        });
    }

    generator_thread.join();
    for (auto& w : workers) w.join();

    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        stop_local = true;
    }
    queue_cv.notify_one();
    py_thread.join();
    pclose(py);
    done_listener_thread.join();

    // === Final Statistics ===
    {
        std::lock_guard<std::mutex> lock(stats_mutex);
        std::cout << "\n===== FINAL STATS =====\n";
        std::cout << "Total tasks completed: " << completed_tasks << "\n";
        std::cout << "Tasks sent to EC:      " << sent_to_ec      << "\n";
        std::cout << "Tasks run locally:     " << ran_on_ed       << "\n";

        double pct_ed = completed_tasks ? (100.0 * ran_on_ed) / completed_tasks : 0.0;
        double pct_ec = completed_tasks ? (100.0 * sent_to_ec) / completed_tasks : 0.0;

        std::cout << "Percent run locally (ED): " << pct_ed << " %\n";
        std::cout << "Percent offloaded (EC):   " << pct_ec << " %\n";

        long corrected_total_latency_ms = total_latency_ms; //The initial value is all EC time.
        int total_count = completed_tasks;

        {
            std::lock_guard<std::mutex> lock2(time_map_mutex);
            for (const auto& [token, end_time] : local_task_end_ms) {
                if (local_task_start_ms.find(token) != local_task_start_ms.end()) {
                    long latency = end_time - local_task_start_ms[token];
                    corrected_total_latency_ms += latency;
                }
            }
        }

        long avg_latency = total_count ? (corrected_total_latency_ms / total_count) : 0;

        std::cout << "Avg latency per task: " << avg_latency << " ms\n";
        std::cout << "========================\n";
    }


    return 0;
}
