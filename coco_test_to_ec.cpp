// ED (Sender) - Send all images to EC and measure transfer time
#include <iostream>
#include <fstream>
#include <vector>
#include <chrono>
#include <dirent.h>
#include <cstring>
#include <arpa/inet.h>
#include <unistd.h>

const char* EC_IP = "192.168.0.100";
const int PORT = 5000;
const char* IMAGE_DIR = "COCO_test_1220";

std::vector<std::string> get_image_files(const std::string& dir_path) {
    std::vector<std::string> files;
    DIR* dir = opendir(dir_path.c_str());
    if (!dir) return files;
    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        if (entry->d_type == DT_REG)
            files.push_back(dir_path + std::string("/") + entry->d_name);
    }
    closedir(dir);
    return files;
}

int main() {
    std::vector<std::string> images = get_image_files(IMAGE_DIR);
    if (images.empty()) {
        std::cerr << "[ED] No images found in directory." << std::endl;
        return 1;
    }

    auto start_all = std::chrono::high_resolution_clock::now();

    for (size_t i = 0; i < images.size(); ++i) {
        const std::string& path = images[i];
        std::ifstream file(path, std::ios::binary);
        if (!file) {
            std::cerr << "[ED] Failed to open image: " << path << std::endl;
            continue;
        }
        file.seekg(0, std::ios::end);
        size_t size = file.tellg();
        file.seekg(0);
        std::vector<char> buffer(size);
        file.read(buffer.data(), size);

        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            perror("[ED] socket error");
            return 1;
        }

        sockaddr_in serv_addr{};
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(PORT);
        inet_pton(AF_INET, EC_IP, &serv_addr.sin_addr);

        if (connect(sock, (sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
            perror("[ED] connect failed");
            close(sock);
            return 1;
        }

        // Send image size first (as 4 bytes)
        uint32_t img_size = static_cast<uint32_t>(size);
        uint32_t net_size = htonl(img_size);
        send(sock, &net_size, sizeof(net_size), 0);
        send(sock, buffer.data(), size, 0);
        close(sock);
    }

    auto end_all = std::chrono::high_resolution_clock::now();
    double total_time_ms = std::chrono::duration<double, std::milli>(end_all - start_all).count();
    double avg_time = total_time_ms / images.size();

    std::cout << "\n===== IMAGE TRANSFER STATS =====" << std::endl;
    std::cout << "Total images sent:   " << images.size() << std::endl;
    std::cout << "Total transfer time: " << total_time_ms << " ms" << std::endl;
    std::cout << "Avg time per image:  " << avg_time << " ms" << std::endl;
    std::cout << "================================" << std::endl;
    return 0;
}
