// C++ CODE (Updated to include full end-to-end average inference time)
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
#include <dirent.h>

const char* EC_IP   = "192.168.0.100";
const int   PORT    = 5000;
const char* IMAGE   = "000000006321.jpg";
const char* PY_CMD  = "python3 rn50_local_run_measure_correct.py";

std::mutex stats_mutex;
int completed_tasks    = 0;
int ran_on_ed          = 0;
int sent_to_ec         = 0;
long total_latency_ms  = 0;

std::mutex queue_mutex;
std::condition_variable queue_cv;
std::queue<std::string> local_queue;
bool stop_local = false;

std::unordered_map<int, double> local_infer_time_ms;
std::unordered_map<int, long> task_start_time;
std::unordered_map<int, long> task_end_time;
std::mutex time_map_mutex;

long current_time_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

void log_result(const std::string& entry) {
    std::lock_guard<std::mutex> lock(stats_mutex);
    std::ofstream log("ed_task_log.txt", std::ios::app);
    log << entry << std::endl;
}

std::string get_random_image_from_coco() {
    std::vector<std::string> images;
    const char* dir_path = "COCO_test_1220";
    DIR* dir = opendir(dir_path);
    if (!dir) return IMAGE;
    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr)
        if (entry->d_type == DT_REG)
            images.emplace_back(std::string(dir_path) + "/" + entry->d_name);
    closedir(dir);
    if (images.empty()) return IMAGE;
    std::mt19937 gen(std::random_device{}());
    std::uniform_int_distribution<> dist(0, images.size() - 1);
    return images[dist(gen)];
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

void enqueue_local_run(int token_ed, const std::string& image_path) {
    std::string task_info = std::to_string(token_ed) + ":" + image_path;
    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        local_queue.push(task_info);
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
        double infer_time_ms = std::stod(line.substr(first + 1, second - first - 1));
        long done_time = std::stol(line.substr(second + 1));
        {
            std::lock_guard<std::mutex> lock(time_map_mutex);
            local_infer_time_ms[token] = infer_time_ms;
            task_end_time[token] = done_time;  // Mark task death time
        }
        log_result("[ED_DONE] token_ed=" + std::to_string(token) + " infer_time=" + std::to_string(infer_time_ms) + " ms");
    }
    fclose(fifo);
}

void run_request(int token_ed) {
    task_start_time[token_ed] = current_time_ms();  // Mark task birth

    auto start = std::chrono::high_resolution_clock::now();
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("[ED] socket failed");
        enqueue_local_run(token_ed, get_random_image_from_coco());
        return;
    }
    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    inet_pton(AF_INET, EC_IP, &serv_addr.sin_addr);
    if (connect(sock, (sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("[ED] connect failed");
        close(sock);
        enqueue_local_run(token_ed, get_random_image_from_coco());
        return;
    }
    std::string req = "REQ:" + std::to_string(token_ed) + ":resnet_50:PI5";
    send(sock, req.c_str(), req.size(), 0);
    char buf[256] = {0};
    int received = recv(sock, buf, sizeof(buf) - 1, 0);
    if (received <= 0) {
        close(sock);
        enqueue_local_run(token_ed, get_random_image_from_coco());
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
        long now_ms = current_time_ms();
        {
            std::lock_guard<std::mutex> lock(time_map_mutex);
            task_end_time[token_ed] = now_ms;  // Mark task death time
        }
        auto end = std::chrono::high_resolution_clock::now();
        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            sent_to_ec++;
        }
        log_result("[ED_SENT] token_ed=" + std::to_string(token_ed) + " token_ec=" + token_ec + " duration=" + std::to_string(duration) + " ms");
    } else if (response == "DROP") {
        enqueue_local_run(token_ed, get_random_image_from_coco());
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            ran_on_ed++;
        }
        log_result("[ED_FALLBACK] token_ed=" + std::to_string(token_ed) + " fallback");
    }
    close(sock);
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: ./ed_oms <lambda_rate> <duration_sec>\n";
        return 1;
    }
    double lambda_rate = std::stod(argv[1]);
    int duration_sec = std::stoi(argv[2]);

    std::atomic<int> total_generated{0};
    std::queue<int> task_queue;
    std::mutex task_queue_mutex;
    std::condition_variable task_queue_cv;
    std::atomic<bool> all_generated{false};

    FILE* py = start_python_helper(duration_sec);
    std::thread py_thread(local_run_dispatch, py);
    std::thread listener_thread(start_done_listener);

    std::mt19937 gen(std::random_device{}());
    std::exponential_distribution<double> dist(lambda_rate);

    std::thread generator([&]() {
        int token = 0;
        auto start = std::chrono::steady_clock::now();
        while (true) {
            auto now = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::seconds>(now - start).count() >= duration_sec) break;

            {
                std::lock_guard<std::mutex> lock(task_queue_mutex);
                task_queue.push(token);
                {
                    std::lock_guard<std::mutex> lock2(time_map_mutex);
                    task_start_time[token] = current_time_ms();  // Mark task birth
                }
                token++;
            }
            total_generated++;
            task_queue_cv.notify_one();
            std::this_thread::sleep_for(std::chrono::duration<double>(dist(gen)));
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
    queue_cv.notify_one();

    py_thread.join();
    pclose(py);
    listener_thread.join();

    double total_local_infer_time = 0;
    int local_infer_count = 0;
    {
        std::lock_guard<std::mutex> lock(time_map_mutex);
        for (auto& kv : local_infer_time_ms) {
            total_local_infer_time += kv.second;
            local_infer_count++;
        }
    }
    double avg_local_infer_time = local_infer_count ? total_local_infer_time / local_infer_count : 0;

    long total_e2e_time = 0;
    int e2e_count = 0;
    {
        std::lock_guard<std::mutex> lock(time_map_mutex);
        for (const auto& kv : task_start_time) {
            int token = kv.first;
            if (task_end_time.count(token)) {
                total_e2e_time += (task_end_time[token] - task_start_time[token]);
                e2e_count++;
            }
        }
    }
    long avg_e2e_latency = e2e_count ? (total_e2e_time / e2e_count) : 0;

    std::cout << "\n===== FINAL STATS =====\n";
    std::cout << "Total tasks completed:   " << completed_tasks << "\n";
    std::cout << "Tasks sent to EC:        " << sent_to_ec << "\n";
    std::cout << "Tasks run locally (DROP):" << ran_on_ed << "\n";
    std::cout << "Avg pure model inference time (DROP): " << avg_local_infer_time << " ms\n";
    std::cout << "Avg total E2E latency (EC + ED):       " << avg_e2e_latency << " ms\n";
    std::cout << "=========================" << std::endl;

    return 0;
}
