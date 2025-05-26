#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdlib>

double compute_column_average(const std::string& filename, int col_index) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "Cannot open file: " << filename << std::endl;
        return -1;
    }

    std::string line;
    double sum = 0.0;
    long count = 0;
    int line_num = 0;

    while (std::getline(infile, line)) {
        line_num++;
        if (line_num == 1) continue;  // skip header

        std::stringstream ss(line);
        std::string cell;
        int current_col = 0;

        while (std::getline(ss, cell, ',')) {
            if (current_col == col_index) {
                try {
                    double val = std::stod(cell);
                    sum += val;
                    count++;
                } catch (...) {
                    // Skip invalid numbers
                }
                break;  // no need to parse further
            }
            current_col++;
        }
    }

    infile.close();
    if (count == 0) {
        std::cerr << "No valid data found in column " << col_index << std::endl;
        return -1;
    }

    return sum / count;
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: ./a.out <file.csv> <column_index>\n";
        return 1;
    }

    std::string filename = argv[1];
    int col_index = std::atoi(argv[2]);

    double average = compute_column_average(filename, col_index);
    if (average >= 0)
        std::cout << "Average of column " << col_index << " from line 2 to end: " << average << std::endl;

    return 0;
}
