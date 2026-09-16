#include "live_display.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

#include <GLFW/glfw3.h>

namespace {

using rgb = std::array<std::uint8_t, 3>;

// Five stops sampled from viridis; depth and cloud use the same palette.
rgb viridis(float value) {
    constexpr std::array<rgb, 5> stops{{
        {{68, 1, 84}}, {{59, 82, 139}}, {{33, 145, 140}},
        {{94, 201, 98}}, {{253, 231, 37}}
    }};
    const float scaled = std::clamp(value, 0.0f, 1.0f) * 4.0f;
    const auto index = std::min(static_cast<std::size_t>(scaled), stops.size() - 2);
    const float fraction = scaled - static_cast<float>(index);
    rgb result{};
    for (std::size_t channel = 0; channel < result.size(); ++channel) {
        result[channel] = static_cast<std::uint8_t>(
            stops[index][channel] * (1.0f - fraction) + stops[index + 1][channel] * fraction);
    }
    return result;
}

float normalized(float value, float low, float high) {
    return high > low ? std::clamp((value - low) / (high - low), 0.0f, 1.0f) : 0.0f;
}

} // namespace

LiveDisplay::LiveDisplay(unsigned int width, unsigned int height)
    : width_(width), height_(height), pixels_(static_cast<std::size_t>(width) * height * 4) {
    if (width == 0 || height == 0 || glfwInit() != GLFW_TRUE) {
        throw std::runtime_error("Cannot initialize GLFW display");
    }
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 2);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 1);
    window_ = glfwCreateWindow(1100, 550, "IMX704 Depth and Point Cloud", nullptr, nullptr);
    if (!window_) {
        glfwTerminate();
        throw std::runtime_error("Cannot open an OpenGL window");
    }
    glfwMakeContextCurrent(window_);
    glfwSwapInterval(1);
    glfwSetWindowUserPointer(window_, this);
    glfwSetMouseButtonCallback(window_, [](GLFWwindow* window, int button, int action, int) {
        auto* self = static_cast<LiveDisplay*>(glfwGetWindowUserPointer(window));
        if (button == GLFW_MOUSE_BUTTON_LEFT) {
            self->dragging_ = action == GLFW_PRESS;
            glfwGetCursorPos(window, &self->cursor_x_, &self->cursor_y_);
        }
    });
    glfwSetCursorPosCallback(window_, [](GLFWwindow* window, double x, double y) {
        auto* self = static_cast<LiveDisplay*>(glfwGetWindowUserPointer(window));
        if (self->dragging_) {
            self->azimuth_ += static_cast<float>((x - self->cursor_x_) * 0.4);
            self->elevation_ = std::clamp(
                self->elevation_ + static_cast<float>((y - self->cursor_y_) * 0.4), -89.0f, 89.0f);
        }
        self->cursor_x_ = x;
        self->cursor_y_ = y;
    });
    glfwSetScrollCallback(window_, [](GLFWwindow* window, double, double y) {
        auto* self = static_cast<LiveDisplay*>(glfwGetWindowUserPointer(window));
        self->distance_ = std::clamp(self->distance_ * std::pow(0.9f, static_cast<float>(y)),
                                     100.0f, 30000.0f);
    });

    glGenTextures(1, &texture_);
    glBindTexture(GL_TEXTURE_2D, texture_);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, static_cast<GLsizei>(width_),
                 static_cast<GLsizei>(height_), 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels_.data());
}

LiveDisplay::~LiveDisplay() {
    if (window_) {
        glfwMakeContextCurrent(window_);
        glDeleteTextures(1, &texture_);
        glfwDestroyWindow(window_);
    }
    glfwTerminate();
}

bool LiveDisplay::is_open() {
    glfwPollEvents();
    if (glfwGetKey(window_, GLFW_KEY_ESCAPE) == GLFW_PRESS) {
        glfwSetWindowShouldClose(window_, GLFW_TRUE);
    }
    return glfwWindowShouldClose(window_) == GLFW_FALSE;
}

void LiveDisplay::update(const std::vector<float>& depth,
                         const std::vector<arducam::depthsense::vector3>& cloud) {
    if (depth.size() != static_cast<std::size_t>(width_) * height_ || cloud.size() != depth.size()) {
        throw std::runtime_error("Unexpected depth or point-cloud size");
    }

    // Match the Python demo: auto-range each frame, mirror X, and mark invalid depth red.
    float low = 0.0f;
    float high = 0.0f;
    bool first = true;
    for (float value : depth) {
        const float safe = std::isfinite(value) ? value : 0.0f;
        if (first) {
            low = high = safe;
            first = false;
        } else {
            low = std::min(low, safe);
            high = std::max(high, safe);
        }
    }
    for (unsigned int y = 0; y < height_; ++y) {
        for (unsigned int x = 0; x < width_; ++x) {
            const float value = depth[static_cast<std::size_t>(y) * width_ + (width_ - 1 - x)];
            const rgb color = !std::isfinite(value) || value == 0.0f
                ? rgb{{255, 0, 0}} : viridis(normalized(value, low, high));
            const auto offset = (static_cast<std::size_t>(y) * width_ + x) * 4;
            pixels_[offset] = color[0];
            pixels_[offset + 1] = color[1];
            pixels_[offset + 2] = color[2];
            pixels_[offset + 3] = 255;
        }
    }
    glBindTexture(GL_TEXTURE_2D, texture_);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, static_cast<GLsizei>(width_),
                    static_cast<GLsizei>(height_), GL_RGBA, GL_UNSIGNED_BYTE, pixels_.data());
    draw(cloud);
}

void LiveDisplay::draw(const std::vector<arducam::depthsense::vector3>& cloud) {
    int framebuffer_width = 0;
    int framebuffer_height = 0;
    glfwGetFramebufferSize(window_, &framebuffer_width, &framebuffer_height);
    if (framebuffer_width <= 0 || framebuffer_height <= 0) {
        return;
    }
    glViewport(0, 0, framebuffer_width, framebuffer_height);
    glClearColor(0.05f, 0.05f, 0.07f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    const int left_width = framebuffer_width / 2;
    const int image_side = std::min(left_width, framebuffer_height);
    glViewport((left_width - image_side) / 2, (framebuffer_height - image_side) / 2,
               image_side, image_side);
    glDisable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, width_, 0, height_, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glEnable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, texture_);
    glColor3ub(255, 255, 255);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 1); glVertex2f(0, 0);
    glTexCoord2f(1, 1); glVertex2f(static_cast<float>(width_), 0);
    glTexCoord2f(1, 0); glVertex2f(static_cast<float>(width_), static_cast<float>(height_));
    glTexCoord2f(0, 0); glVertex2f(0, static_cast<float>(height_));
    glEnd();
    glDisable(GL_TEXTURE_2D);

    const int right_width = framebuffer_width - left_width;
    glViewport(left_width, 0, right_width, framebuffer_height);
    const double near_plane = 10.0;
    const double half_height = near_plane * std::tan(45.0 * 3.141592653589793 / 360.0);
    const double half_width = half_height * right_width / framebuffer_height;
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glFrustum(-half_width, half_width, -half_height, half_height, near_plane, 50000.0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glTranslatef(0, 0, -distance_);
    glRotatef(elevation_, 1, 0, 0);
    glRotatef(azimuth_, 0, 1, 0);
    glEnable(GL_DEPTH_TEST);
    glPointSize(7.0f);

    float z_low = 0.0f;
    float z_high = 0.0f;
    bool first = true;
    for (const auto& point : cloud) {
        if (!std::isfinite(point.x) || !std::isfinite(point.y) ||
            !std::isfinite(point.z) || point.z <= 0) continue;
        if (first) {
            z_low = z_high = point.z;
            first = false;
        } else {
            z_low = std::min(z_low, point.z);
            z_high = std::max(z_high, point.z);
        }
    }
    glBegin(GL_POINTS);
    for (const auto& point : cloud) {
        if (!std::isfinite(point.x) || !std::isfinite(point.y) ||
            !std::isfinite(point.z) || point.z <= 0) continue;
        const rgb color = viridis(normalized(point.z, z_low, z_high));
        glColor3ub(color[0], color[1], color[2]);
        glVertex3f(point.x, point.y, -point.z);
    }
    glEnd();
    glfwSwapBuffers(window_);
}
