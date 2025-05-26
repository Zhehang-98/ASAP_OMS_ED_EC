// File: ed_oms.cpp

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

const char* EC_IP       = "192.168.0.109";
const int   PORT        = 5000;
const char* IMAGE       = "COCO_test_1220/000000006321.jpg";
// Python fallback helper in “serve” mode:
const char* PY_CMD      = "python3 ED_OMS/rn50_local_run.py COCO_test_1220/000000006321.jpg";

std::mutex stats_mutex;
int completed_tasks    = 0;
int ran_on_ed          = 0;
int sent_to_ec         = 0;
long total_latency_ms  = 0;

// Queue for images that need local processing:
std::mutex               queue_mutex;
std::condition_variable  queue_cv;
bool                     stop_local = false;
std::queue<std::string>  local_queue;

void log_result(const std::string& entry) {
    std::lock_guard<std::mutex> lk(stats_mutex);
    std::ofstream log("ed_task_log.txt", std::ios::app);
    log << entry << "\n";
}

int generate_poisson_delay(double lambda) {
    static std::default_random_engine gen(std::random_device{}());
    std::exponential_distribution<double> dist(lambda);
    return int(dist(gen) * 1000);
}

// Launch Python server once at startup:
FILE* start_python_helper() {
    FILE* py = popen(PY_CMD, "w");
    if (!py) {
        std::cerr << "[ED] Failed to launch python helper\n";
        exit(1);
    }
    return py;
}

// Enqueue an image path for the python helper to process:
void enqueue_local_run(const std::string& img) {
    {
        std::lock_guard<std::mutex> lk(queue_mutex);
        local_queue.push(img);
    }
    queue_cv.notify_one();
}

void run_request(int token_ed) {
    auto start = std::chrono::high_resolution_clock::now();
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("[ED] socket");
        return;
    }

    sockaddr_in serv{};
    serv.sin_family = AF_INET;
    serv.sin_port   = htons(PORT);
    inet_pton(AF_INET, EC_IP, &serv.sin_addr);

    if (connect(sock, (sockaddr*)&serv, sizeof(serv)) < 0) {
        // Network failure → fallback locally
        enqueue_local_run(IMAGE);
        auto end = std::chrono::high_resolution_clock::now();
        long dur = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        {
            std::lock_guard<std::mutex> lk(stats_mutex);
            completed_tasks++;
            total_latency_ms += dur;
            ran_on_ed++;
        }
        log_result("[ED_LOCAL] token=" + std::to_string(token_ed) + " dur=" + std::to_string(dur));
        close(sock);
        return;
    }

    // Send offload request
    std::string req = "REQ:" + std::to_string(token_ed) + ":resnet_50:PI5";
    send(sock, req.c_str(), req.size(), 0);

    char buf[256] = {};
    int n = recv(sock, buf, sizeof(buf)-1, 0);
    if (n > 0) {
        std::string resp(buf, n);
        if (resp.rfind("GRANT:", 0) == 0) {
            // Offload success
            sent_to_ec++;
        } else if (resp == "DROP") {
            // Explicit DROP → fallback locally
            enqueue_local_run(IMAGE);
            auto end = std::chrono::high_resolution_clock::now();
            long dur = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
            {
                std::lock_guard<std::mutex> lk(stats_mutex);
                completed_tasks++;
                total_latency_ms += dur;
                ran_on_ed++;
            }
            log_result("[ED_DROP] token=" + std::to_string(token_ed) + " dur=" + std::to_string(dur));
        }
    }
    close(sock);
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: ./ed_oms <lambda> <num_tasks>\n";
        return 1;
    }
    double lambda      = std::stod(argv[1]);
    int total_requests = std::stoi(argv[2]);

    // 1) Start Python helper
    FILE* py = start_python_helper();

    // Thread to feed Python helper from queue
    std::thread py_thread([&](){
        while (true) {
            std::unique_lock<std::mutex> lk(queue_mutex);
            queue_cv.wait(lk, []{ return !local_queue.empty() || stop_local; });
            if (stop_local && local_queue.empty()) break;
            auto img = std::move(local_queue.front());
            local_queue.pop();
            lk.unlock();
            // send image path to python
            fprintf(py, "%s\n", img.c_str());
            fflush(py);
        }
    });

    // 2) Issue requests
    std::vector<std::thread> threads;
    for (int i = 0; i < total_requests; ++i) {
        int d = generate_poisson_delay(lambda);
        std::this_thread::sleep_for(std::chrono::milliseconds(d));
        threads.emplace_back(run_request, i);
    }
    for (auto& t : threads) t.join();

    // 3) Stop Python helper and gather resource usage
    {
        std::lock_guard<std::mutex> lk(queue_mutex);
        stop_local = true;
    }
    queue_cv.notify_one();
    py_thread.join();
    pclose(py);

    // Get resource usage of python child
    struct rusage usage;
    getrusage(RUSAGE_CHILDREN, &usage);
    double cpu_sec = usage.ru_utime.tv_sec + usage.ru_utime.tv_usec/1e6
                   + usage.ru_stime.tv_sec + usage.ru_stime.tv_usec/1e6;
    long max_rss_kb = usage.ru_maxrss; // in kilobytes
    long cores      = sysconf(_SC_NPROCESSORS_ONLN);

    // 4) Print final stats
    {
        std::lock_guard<std::mutex> lk(stats_mutex);
        std::cout << "\n===== FINAL STATS =====\n";
        std::cout << "Completed tasks:      " << completed_tasks << "\n";
        std::cout << "Tasks run locally:    " << ran_on_ed       << "\n";
        std::cout << "Tasks offloaded:      " << sent_to_ec      << "\n";
        std::cout << "Avg LAT (ms/task):   "
                  << (completed_tasks ? total_latency_ms / completed_tasks : 0)
                  << "\n\n-- Local Fallback Resource Usage --\n";
        std::cout << "Python CPU time:      " << cpu_sec/1.0 << " s\n";
        std::cout << "Python peak memory:   " << (max_rss_kb/1024.0) << " MB\n";
        std::cout << "Available cores:      " << cores       << "\n";
        std::cout << "========================\n";
    }
    return 0;
}
