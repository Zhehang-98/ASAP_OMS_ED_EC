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

#include <iomanip>  // for std::setprecision

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

void receive_one_result(const std::string& ec_ip, int file_idx) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server{};
    server.sin_family = AF_INET;
    server.sin_port = htons(5001);
    inet_pton(AF_INET, ec_ip.c_str(), &server.sin_addr);
    connect(sock, (sockaddr*)&server, sizeof(server));

    std::string init = "GET";
    send(sock, init.c_str(), init.size(), 0);

    // 接收数量（应该是 1）
    char buf[16];
    recv(sock, buf, 16, 0);
    int num_files = std::stoi(buf);

    if (num_files != 1) {
        std::cerr << "[ED] Unexpected number of files: " << num_files << "\n";
        close(sock);
        return;
    }

    // 接收并保存一个文件
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

    std::string new_name = "result_" + std::to_string(file_idx) + ".txt";
    std::ofstream out(new_name);
    out.write(file_data.data(), file_data.size());

    // std::cout << "[ED] Saved " << new_name << " (" << fsize << " bytes)\n";
    close(sock);
}

int main(int argc, char* argv[]) {
    if (argc != 3 || std::string(argv[1]) != "GET") {
        std::cerr << "Usage: ./ed_transfer GET <ec_ip>\n";
        return 1;
    }

    std::string ec_ip = argv[2];
    const int total_files = 1220;

    auto start = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < total_files; ++i) {
        receive_one_result(ec_ip, i);
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    double total_sec = elapsed.count();
    double avg_ms = (total_sec * 1000.0) / total_files;

    std::cout << std::fixed << std::setprecision(6);
    std::cout << "[ED] Received " << total_files << " files\n";
    std::cout << "[ED] Total time: " << total_sec << " sec\n";
    std::cout << "[ED] Average per file: " << avg_ms << " ms\n";

    return 0;
}