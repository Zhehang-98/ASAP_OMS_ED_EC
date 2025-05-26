/*
g++ -std=c++17 -O2 -I. -o EC_OMS_May15_model1 EC_OMS_May15_YOLOv5s6.cpp     -lvitis_ai_library-yolov3     -lvitis_ai_library-dpu_task     -lvitis_ai_library-xnnpp     -lvitis_ai_library-model_config     -lvitis_ai_library-math     -lvart-util     -lxir     -pthread     -ljson-c     -lglog     $(pkg-config --cflags --libs opencv4 || pkg-config --cflags --libs opencv)
*/

#include <iostream>
#include <thread>
#include <vector>
#include <mutex>
#include <chrono>
#include <cstring>
#include <fstream>
#include <opencv2/opencv.hpp>
// #include <vitis/ai/classification.hpp>
#include <vitis/ai/yolov3.hpp>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstdlib>

const int PORT = 5000;
std::mutex queue_mutex;

int queue_size = 0;
int tasks_on_ec = 0;
int tasks_dropped = 0;

// Shared model instance
auto model = vitis::ai::YOLOv3::create("yolov5s6_pt");

void handle_request(int client_socket) {
    char buffer[256] = {0};
    recv(client_socket, buffer, 255, 0);
    std::string request(buffer);

    if (request.rfind("REQ:", 0) == 0) {
        size_t pos1 = request.find(':');
        size_t pos2 = request.find(':', pos1 + 1);
        std::string token_ed = request.substr(pos1 + 1, pos2 - pos1 - 1);

        int local_queue;
        {
            std::lock_guard<std::mutex> lock(queue_mutex);
            local_queue = queue_size++;
        }

        int wait_ms = static_cast<int>(local_queue * 68.71);
        if (wait_ms <= 550) {
            int token_ec = local_queue;
            std::string grant = "GRANT:" + std::to_string(token_ec);
            send(client_socket, grant.c_str(), grant.size(), 0);
            std::cout << "[EC] Sent GRANT to ED for token_ed=" << token_ed << ", token_ec=" << token_ec << "\n";

            char ack_buf[256] = {0};
            recv(client_socket, ack_buf, 255, 0);

            std::string ack(ack_buf);
            if (ack.rfind("OK:", 0) == 0) {
                std::cout << "[EC] Receiving image for token_ec=" << token_ec << "...\n";

                // Just load from disk — ignore what was sent
                cv::Mat image = cv::imread("COCO_test_1220/000000000664.jpg");

                
                // No need to check if empty
                std::cout << "[EC] Running DPU inference on static image...\n";
                auto result = model->run(image);

                // results part we need to change
                for (const auto& bbox : result.bboxes) {
                    std::cout << "Label: " << bbox.label
                            << ", Score: " << bbox.score
                            << ", BBox: [" << bbox.x << ", " << bbox.y
                            << ", " << bbox.width << ", " << bbox.height << "]\n";
                }

                std::string done_msg = "DONE";
                send(client_socket, done_msg.c_str(), done_msg.size(), 0);

                {
                    std::lock_guard<std::mutex> lock(queue_mutex);
                    tasks_on_ec++;
                    queue_size--;
                }

                std::cout << "[EC] Completed task for token_ed=" << token_ed << ", token_ec=" << token_ec << "\n";
            }
        } else {
            std::string drop = "DROP";
            send(client_socket, drop.c_str(), drop.size(), 0);
            std::cout << "[EC] Sent DROP for token_ed=" << token_ed << " (wait=" << wait_ms << "ms)\n";

            {
                std::lock_guard<std::mutex> lock(queue_mutex);
                tasks_dropped++;
                queue_size--;
            }
        }

        std::cout << "[EC] Queue Size: " << queue_size
                  << ", Tasks on EC: " << tasks_on_ec
                  << ", Dropped to ED: " << tasks_dropped << "\n";
    }

    close(client_socket);
}

int main() {
    if (!model) {
        std::cerr << "[EC] Failed to create model instance.\n";
        return 1;
    }

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) { perror("socket"); exit(EXIT_FAILURE); }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (sockaddr*)&address, sizeof(address)) < 0) {
        perror("bind"); exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 20) < 0) {
        perror("listen"); exit(EXIT_FAILURE);
    }

    std::cout << "[EC] Listening on port " << PORT << "\n";

    while (true) {
        sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        int new_socket = accept(server_fd, (sockaddr*)&client_addr, &client_len);
        if (new_socket < 0) { perror("accept"); continue; }

        std::thread(handle_request, new_socket).detach();
    }

    return 0;
}
