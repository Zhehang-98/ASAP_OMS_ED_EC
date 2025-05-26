// ed_transfer.cpp (Edge Device - C++)
#include <iostream>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <cstring>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <vector>

namespace fs = std::filesystem;

void send_images(const std::string& local_dir, const std::string& remote_dir, const std::string& ec_ip) {
    auto start = std::chrono::high_resolution_clock::now();
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server{};
    server.sin_family = AF_INET;
    server.sin_port = htons(5001);
    inet_pton(AF_INET, ec_ip.c_str(), &server.sin_addr);
    connect(sock, (sockaddr*)&server, sizeof(server));

    std::string init = "SEND " + remote_dir;
    send(sock, init.c_str(), init.size(), 0);

    std::vector<fs::path> images;
    for (const auto& file : fs::directory_iterator(local_dir))
        if (file.path().extension() == ".jpg") images.push_back(file.path());

    std::string num_files = std::to_string(images.size());
    send(sock, num_files.c_str(), 16, 0);

    for (const auto& img : images) {
        std::string fname = img.filename().string();
        std::string name_len = std::to_string(fname.size());
        send(sock, name_len.c_str(), 8, 0);
        send(sock, fname.c_str(), fname.size(), 0);

        std::ifstream f(img, std::ios::binary);
        std::vector<char> buffer((std::istreambuf_iterator<char>(f)), {});
        std::string fsize = std::to_string(buffer.size());
        send(sock, fsize.c_str(), 16, 0);
        send(sock, buffer.data(), buffer.size(), 0);
    }
    close(sock);
    auto end = std::chrono::high_resolution_clock::now();
    double elapsed = std::chrono::duration<double>(end - start).count();
    std::cout << "[ED] Sent " << images.size() << " images in " << elapsed << " s\nAvg: " << elapsed / images.size() << " s/image\n";
}

void receive_images(const std::string& remote_dir, const std::string& local_dir, const std::string& ec_ip) {
    auto start = std::chrono::high_resolution_clock::now();
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server{};
    server.sin_family = AF_INET;
    server.sin_port = htons(5001);
    inet_pton(AF_INET, ec_ip.c_str(), &server.sin_addr);
    connect(sock, (sockaddr*)&server, sizeof(server));

    std::string init = "GET " + remote_dir;
    send(sock, init.c_str(), init.size(), 0);

    char buf[16];
    recv(sock, buf, 16, 0);
    int num_files = std::stoi(buf);

    for (int i = 0; i < num_files; ++i) {
        recv(sock, buf, 8, 0);
        int name_len = std::stoi(std::string(buf, 8));
        std::string fname(name_len, 0);
        recv(sock, fname.data(), name_len, 0);

        recv(sock, buf, 16, 0);
        int fsize = std::stoi(std::string(buf, 16));
        std::vector<char> file_data(fsize);
        int received = 0;
        while (received < fsize) {
            int chunk = recv(sock, file_data.data() + received, fsize - received, 0);
            if (chunk <= 0) break;
            received += chunk;
        }
        std::ofstream out(local_dir + "/" + fname, std::ios::binary);
        out.write(file_data.data(), file_data.size());
    }
    close(sock);
    auto end = std::chrono::high_resolution_clock::now();
    double elapsed = std::chrono::duration<double>(end - start).count();
    std::cout << "[ED] Received " << num_files << " images in " << elapsed << " s\nAvg: " << elapsed / num_files << " s/image\n";
}

int main(int argc, char* argv[]) {
    if (argc != 5) {
        std::cerr << "Usage: ./ed_transfer SEND <local_dir> <remote_dir> <ec_ip>\n"
                  << "    or: ./ed_transfer GET <remote_dir> <local_dir> <ec_ip>\n";
        return 1;
    }
    std::string mode = argv[1];
    if (mode == "SEND") send_images(argv[2], argv[3], argv[4]);
    else if (mode == "GET") receive_images(argv[2], argv[3], argv[4]);
    else std::cerr << "Invalid mode. Use SEND or GET.\n";
    return 0;
}

