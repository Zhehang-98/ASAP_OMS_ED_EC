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
        std::string remote_dir = mode.substr(4);
        std::vector<std::string> files;
        for (const auto& f : fs::directory_iterator(remote_dir))
            if (f.path().extension() == ".jpg")
                files.push_back(f.path().filename().string());

        std::string num = std::to_string(files.size());
        send(client_sock, num.c_str(), 16, 0);

        for (const auto& fname : files) {
            std::string path = remote_dir + "/" + fname;
            std::ifstream in(path, std::ios::binary);
            std::vector<char> data((std::istreambuf_iterator<char>(in)), {});
            std::string name_len = std::to_string(fname.size());
            std::string fsize = std::to_string(data.size());

            send(client_sock, name_len.c_str(), 8, 0);
            send(client_sock, fname.c_str(), fname.size(), 0);
            send(client_sock, fsize.c_str(), 16, 0);
            send(client_sock, data.data(), data.size(), 0);
        }
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
