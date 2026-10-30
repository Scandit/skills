// opencv_app.cpp - quality-control tool: loads label photos with OpenCV and should report the
// QR and Data Matrix codes on them.
// Build: g++ -O2 -std=c++17 -o qc opencv_app.cpp $(pkg-config --cflags --libs opencv4)
#include <cstdio>
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>

int main(int argc, char **argv) {
    for (int i = 1; i < argc; ++i) {
        cv::Mat image = cv::imread(argv[i], cv::IMREAD_COLOR);
        if (image.empty()) { std::fprintf(stderr, "%s: cannot read\n", argv[i]); continue; }
        // TODO: decode the codes in `image` with the Scandit SDK
        std::printf("%s: %dx%d\n", argv[i], image.cols, image.rows);
    }
    return 0;
}
