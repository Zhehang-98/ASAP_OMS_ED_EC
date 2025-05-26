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
#include <condition_variable>

const char* EC_IP = "192.168.0.109";
const int PORT = 5000;
const char* IMAGE = "COCO_test_1220/000000006321.jpg";
const char* LOCAL_CMD = "python3 retinaface_detect.py ~/COCO_test_1220/000000000664.jpg";

std::mutex stats_mutex;
std::mutex local_mutex;
int local_running = 0;
const int MAX_LOCAL = 20;

int completed_tasks = 0;
int ran_on_ed = 0;
int sent_to_ec = 0;
long total_latency_ms = 0;

// ========== Counting Semaphore (C++17 version) ==========
class SimpleSemaphore {
private:
    std::mutex mtx;
    std::condition_variable cv;
    int count;
public:
    explicit SimpleSemaphore(int initial) : count(initial) {}
    void acquire() {
        std::unique_lock<std::mutex> lock(mtx);
        cv.wait(lock, [&]() { return count > 0; });
        --count;
    }
    void release() {
        std::unique_lock<std::mutex> lock(mtx);
        ++count;
        cv.notify_one();
    }
};
SimpleSemaphore thread_limit(100);  // max 100 concurrent threads
// =======================================================

void log_result(const std::string& entry) {
    std::lock_guard<std::mutex> lock(stats_mutex);
    std::ofstream log("ed_task_log.txt", std::ios::app);
    log << entry << std::endl;
}

int generate_poisson_delay(double lambda) {
    static std::default_random_engine gen(std::random_device{}());
    std::exponential_distribution<double> dist(lambda);
    return static_cast<int>(dist(gen) * 1000);
}

void run_request(int token_ed) {
    thread_limit.acquire();
    auto start = std::chrono::high_resolution_clock::now();

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        std::cerr << "[ED] Socket error\n";
        thread_limit.release();
        return;
    }

    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    inet_pton(AF_INET, EC_IP, &serv_addr.sin_addr);

    if (connect(sock, (sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        std::cerr << "[ED] Connection to EC failed. Running locally.\n";

        while (true) {
            {
                std::lock_guard<std::mutex> lock(local_mutex);
                if (local_running < MAX_LOCAL) {
                    local_running++;
                    break;
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }

        std::system(LOCAL_CMD);

        {
            std::lock_guard<std::mutex> lock(local_mutex);
            local_running--;
        }

        auto end = std::chrono::high_resolution_clock::now();
        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            ran_on_ed++;
        }

        log_result("[ED_LOCAL_FAILOVER] token=" + std::to_string(token_ed) + " duration=" + std::to_string(duration));
        close(sock);
        thread_limit.release();
        return;
    }

    std::string req = "REQ:" + std::to_string(token_ed) + ":retinaface:PI5";
    send(sock, req.c_str(), req.size(), 0);
    std::cout << "[ED] Sent request: token_ed=" << token_ed << std::endl;

    char buf[256] = {0};
    recv(sock, buf, 255, 0);
    std::string response(buf);

    if (response.rfind("GRANT:", 0) == 0) {
        std::string token_ec = response.substr(6);
        std::string ok_msg = "OK:" + token_ec + ":" + std::to_string(token_ed);
        send(sock, ok_msg.c_str(), ok_msg.size(), 0);

        std::ifstream file(IMAGE, std::ios::binary);
        if (!file) {
            std::cerr << "[ED] Image not found.\n";
            close(sock);
            thread_limit.release();
            return;
        }

        char img_buf[4096];
        while (file.read(img_buf, sizeof(img_buf)))
            send(sock, img_buf, file.gcount(), 0);
        if (file.gcount() > 0)
            send(sock, img_buf, file.gcount(), 0);
        file.close();

        shutdown(sock, SHUT_WR);

        std::cout << "[ED] Image sent: token_ed=" << token_ed << " token_ec=" << token_ec << std::endl;

        char done_buf[16] = {0};
        int bytes = recv(sock, done_buf, sizeof(done_buf) - 1, 0);
        std::string done_msg(done_buf, bytes);

        if (done_msg == "DONE") {
            auto end = std::chrono::high_resolution_clock::now();
            long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

            {
                std::lock_guard<std::mutex> lock(stats_mutex);
                completed_tasks++;
                total_latency_ms += duration;
                sent_to_ec++;
            }

            std::cout << "[ED] DONE received for token_ed=" << token_ed
                      << " | duration=" << duration << " ms\n";

            log_result("[ED_SENT] token_ed=" + std::to_string(token_ed) +
                       " token_ec=" + token_ec + " duration=" + std::to_string(duration) + " ms");
        } else {
            std::cerr << "[ED] Unexpected message: " << done_msg << "\n";
        }

    } else if (response == "DROP") {
        std::cout << "[ED] DROP received for token_ed=" << token_ed << ". Running locally.\n";

        while (true) {
            {
                std::lock_guard<std::mutex> lock(local_mutex);
                if (local_running < MAX_LOCAL) {
                    local_running++;
                    break;
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }

        std::system(LOCAL_CMD);

        {
            std::lock_guard<std::mutex> lock(local_mutex);
            local_running--;
        }

        auto end = std::chrono::high_resolution_clock::now();
        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            ran_on_ed++;
        }

        log_result("[ED_LOCAL] token_ed=" + std::to_string(token_ed) +
                   " duration=" + std::to_string(duration) + " ms");
    }

    close(sock);
    thread_limit.release();
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: ./ed_oms <lambda> <num_tasks>\n";
        return 1;
    }

    double lambda = std::stod(argv[1]);
    int total_requests = std::stoi(argv[2]);

    std::vector<std::thread> threads;

    for (int i = 0; i < total_requests; ++i) {
        int delay = generate_poisson_delay(lambda);
        std::this_thread::sleep_for(std::chrono::milliseconds(delay));
        threads.emplace_back(run_request, i);

        // Light backoff to ease scheduler pressure
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    for (auto& t : threads) t.join();

    {
        std::lock_guard<std::mutex> lock(stats_mutex);
        std::cout << "\n===== FINAL STATS =====\n";
        std::cout << "Total tasks completed: " << completed_tasks << "\n";
        std::cout << "Tasks sent to EC: " << sent_to_ec << "\n";
        std::cout << "Tasks run locally: " << ran_on_ed << "\n";
        std::cout << "Avg Total End-to-End Latency per Task: "
                  << (completed_tasks ? total_latency_ms / completed_tasks : 0) << " ms\n";
        std::cout << "========================\n";
    }

    return 0;
}
