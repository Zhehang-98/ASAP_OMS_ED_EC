// ec_transfer.cpp (Edge Cloud - C++)
#include <iostream>
#include <fstream>
#include <filesystem>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <vector>

namespace fs = std::filesystem;
const int PORT = 5001;

void handle_client(int client_sock) {
    char buffer[1024] = {0};
    recv(client_sock, buffer, sizeof(buffer), 0);
    std::string mode(buffer);

    if (mode.find("SEND") == 0) {
        std::string remote_dir = mode.substr(5);
        fs::create_directories(remote_dir);

        char num_buf[16];
        recv(client_sock, num_buf, 16, 0);
        int num_files = std::stoi(num_buf);

        for (int i = 0; i < num_files; ++i) {
            char len_buf[8];
            recv(client_sock, len_buf, 8, 0);
            int name_len = std::stoi(std::string(len_buf, 8));

            std::string fname(name_len, 0);
            recv(client_sock, fname.data(), name_len, 0);

            char size_buf[16];
            recv(client_sock, size_buf, 16, 0);
            int fsize = std::stoi(std::string(size_buf, 16));

            std::vector<char> file_data(fsize);
            int received = 0;
            while (received < fsize) {
                int chunk = recv(client_sock, file_data.data() + received, fsize - received, 0);
                if (chunk <= 0) break;
                received += chunk;
            }

            std::ofstream out(remote_dir + "/" + fname, std::ios::binary);
            out.write(file_data.data(), file_data.size());
        }
    } else if (mode.find("GET") == 0) {
        // 只返回 1 个结果
        int num_results = 1;
        std::string num = std::to_string(num_results);
        send(client_sock, num.c_str(), 16, 0);  // 先发数量

        // 构造 1024B 的字符串
        std::string payload;
        while (payload.size() < 1024)
            payload += "ABCD";  // 256 次 ABCD = 1024 字节

        // 发送 1 个模拟的文本文件
        std::string fname = "result.txt";
        std::string name_len = std::to_string(fname.size());
        std::string fsize = std::to_string(payload.size());

        send(client_sock, name_len.c_str(), 8, 0);
        send(client_sock, fname.c_str(), fname.size(), 0);
        send(client_sock, fsize.c_str(), 16, 0);
        send(client_sock, payload.c_str(), payload.size(), 0);

        std::cout << "[EC] Sent 1 file of 1024B to ED\n";
    }

    close(client_sock);
}

int main() {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(PORT);

    bind(server_fd, (sockaddr*)&addr, sizeof(addr));
    listen(server_fd, 5);

    std::cout << "[EC] Listening on port " << PORT << "...\n";
    while (true) {
        int client = accept(server_fd, nullptr, nullptr);
        handle_client(client);
    }
    return 0;
}
