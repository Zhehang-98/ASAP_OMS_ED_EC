// EC (Receiver) - Accepts images sent from ED and acknowledges receipt
#include <iostream>
#include <fstream>
#include <vector>
#include <chrono>
#include <arpa/inet.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <cstring>

const int PORT = 5000;

int main() {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == 0) {
        perror("[EC] Socket failed");
        return 1;
    }

    sockaddr_in address{};
    int addrlen = sizeof(address);
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt));

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("[EC] Bind failed");
        return 1;
    }
    if (listen(server_fd, 10) < 0) {
        perror("[EC] Listen failed");
        return 1;
    }

    std::cout << "[EC] Listening on port " << PORT << "..." << std::endl;
    int received_images = 0;

    while (true) {
        int new_socket = accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen);
        if (new_socket < 0) {
            perror("[EC] Accept failed");
            continue;
        }

        uint32_t net_size;
        int bytes_read = recv(new_socket, &net_size, sizeof(net_size), 0);
        if (bytes_read != sizeof(net_size)) {
            std::cerr << "[EC] Failed to read image size." << std::endl;
            close(new_socket);
            continue;
        }

        uint32_t img_size = ntohl(net_size);
        std::vector<char> buffer(img_size);
        size_t total_received = 0;
        while (total_received < img_size) {
            int chunk = recv(new_socket, buffer.data() + total_received, img_size - total_received, 0);
            if (chunk <= 0) break;
            total_received += chunk;
        }

        if (total_received == img_size) {
            received_images++;
            std::cout << "[EC] Received image " << received_images << " (" << img_size << " bytes)" << std::endl;
        } else {
            std::cerr << "[EC] Incomplete image received." << std::endl;
        }

        close(new_socket);
    }

    close(server_fd);
    return 0;
}
