#pragma once

#include <cstdint>
#include <vector>

#include <imx704_camera/vector3.h>

struct GLFWwindow;

class LiveDisplay {
public:
    LiveDisplay(unsigned int width, unsigned int height);
    ~LiveDisplay();

    LiveDisplay(const LiveDisplay&) = delete;
    LiveDisplay& operator=(const LiveDisplay&) = delete;

    bool is_open();
    void update(const std::vector<float>& depth,
                const std::vector<arducam::depthsense::vector3>& cloud);

private:
    GLFWwindow* window_ = nullptr;
    unsigned int texture_ = 0;
    unsigned int width_;
    unsigned int height_;
    std::vector<std::uint8_t> pixels_;
    float azimuth_ = 30.0f;
    float elevation_ = 30.0f;
    float distance_ = 2500.0f;
    bool dragging_ = false;
    double cursor_x_ = 0;
    double cursor_y_ = 0;

    void draw(const std::vector<arducam::depthsense::vector3>& cloud);
};
