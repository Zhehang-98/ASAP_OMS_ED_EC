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

const char* EC_IP = "192.168.0.100";  // Replace with actual EC IP
const int PORT = 5000;
const char* IMAGE = "COCO_test_1220/000000006321.jpg";
const char* LOCAL_CMD = "python3 ED_OMS/rn50_local_run.py COCO_test_1220/000000006321.jpg";

std::mutex stats_mutex;
int completed_tasks = 0;
int ran_on_ed = 0;
int sent_to_ec = 0;
long total_latency_ms = 0;

void log_result(const std::string& entry) {
    std::lock_guard<std::mutex> lock(stats_mutex);
    std::ofstream log("ed_task_log.txt", std::ios::app);
    log << entry << std::endl;
}

int generate_poisson_delay(double lambda) {
    static std::default_random_engine gen(std::random_device{}());
    std::exponential_distribution<double> dist(lambda);
    return static_cast<int>(dist(gen) * 1000); // milliseconds
}

void run_request(int token_ed) {
    auto start = std::chrono::high_resolution_clock::now();

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        std::cerr << "[ED] Socket error\n";
        return;
    }

    sockaddr_in serv_addr{};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
    inet_pton(AF_INET, EC_IP, &serv_addr.sin_addr);

    if (connect(sock, (sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
        std::cerr << "[ED] Connection to EC failed. Running locally.\n";
        std::system(LOCAL_CMD);
        auto end = std::chrono::high_resolution_clock::now();

        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            
        }

        log_result("[ED_LOCAL_FAILOVER] token=" + std::to_string(token_ed) + " duration=" + std::to_string(duration));
        return;
    }

    std::string req = "REQ:" + std::to_string(token_ed) + ":resnet_50:PI5";
    send(sock, req.c_str(), req.size(), 0);
    std::cout << "[ED] Sent request: token_ed=" << token_ed << std::endl;

    char buf[256] = {0};
    recv(sock, buf, 255, 0);
    std::string response(buf);

    if (response.rfind("GRANT:", 0) == 0) {
        std::string token_ec = response.substr(6);
        std::string ok_msg = "OK:" + token_ec + ":" + std::to_string(token_ed);
        send(sock, ok_msg.c_str(), ok_msg.size(), 0);
        std::this_thread::sleep_for(std::chrono::milliseconds(5));

        std::ifstream file(IMAGE, std::ios::binary);
        if (!file) {
            std::cerr << "[ED] Image not found.\n";
            close(sock);
            return;
        }

        char img_buf[4096];
        while (file.read(img_buf, sizeof(img_buf)))
            send(sock, img_buf, file.gcount(), 0);
        file.close();

        auto end = std::chrono::high_resolution_clock::now();
        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            sent_to_ec++;
        }

        std::cout << "[ED] Image sent: token_ed=" << token_ed << " token_ec=" << token_ec << std::endl;
        
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
                    }
log_result("[ED_SENT] token_ed=" + std::to_string(token_ed) + " token_ec=" + token_ec + " duration=" + std::to_string(duration) + " ms");
    } else if (response == "DROP") {
        std::cout << "[ED] DROP received for token_ed=" << token_ed << ". Running locally.\n";
        std::system(LOCAL_CMD);
        auto end = std::chrono::high_resolution_clock::now();

        long duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        {
            std::lock_guard<std::mutex> lock(stats_mutex);
            completed_tasks++;
            total_latency_ms += duration;
            ran_on_ed++;
        }

        log_result("[ED_LOCAL] token_ed=" + std::to_string(token_ed) + " duration=" + std::to_string(duration) + " ms");
    }

    close(sock);
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
        std::this_thread::sleep_for(std::chrono::milliseconds(delay));
        run_request(i);
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
        std::cout << "========================\n" << std::flush;
    
            

    return 0;
}
}
