#include <cerrno>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <string>
#include <thread>

#include <imx704_camera/camera.h>
#include <imx704_camera/camera_manager.h>

using namespace arducam::depthsense;

namespace {

struct options {
    bool list_only = false;
    unsigned int camera_index = 0;
    unsigned int mode = 0x311C;
    unsigned int frames = 10;
    unsigned int timeout_ms = 100;
    unsigned int startup_delay_ms = 2000;
};

void usage(const char* name) {
    std::cout << "Usage: " << name << " [--list] [--camera-index N] [--mode HEX]"
              << " [--frames N] [--timeout-ms N] [--startup-delay-ms N]\n";
}

bool parse_unsigned(const char* text, unsigned int& value, int base = 10) {
    if (text[0] == '-' || text[0] == '\0') return false;
    errno = 0;
    char* end = nullptr;
    const unsigned long parsed = std::strtoul(text, &end, base);
    if (errno != 0 || *end != '\0' || parsed > std::numeric_limits<unsigned int>::max())
        return false;
    value = static_cast<unsigned int>(parsed);
    return true;
}

bool parse_args(int argc, char** argv, options& opts) {
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        if (arg == "--help" || arg == "-h") {
            usage(argv[0]);
            std::exit(0);
        }
        if (arg == "--list") {
            opts.list_only = true;
            continue;
        }
        if (i + 1 >= argc) return false;
        unsigned int* target = nullptr;
        int base = 10;
        if (arg == "--camera-index") target = &opts.camera_index;
        else if (arg == "--mode") { target = &opts.mode; base = 16; }
        else if (arg == "--frames") target = &opts.frames;
        else if (arg == "--timeout-ms") target = &opts.timeout_ms;
        else if (arg == "--startup-delay-ms") target = &opts.startup_delay_ms;
        else return false;
        if (!parse_unsigned(argv[++i], *target, base)) return false;
    }
    return opts.list_only || (opts.frames > 0 && opts.timeout_ms > 0);
}

struct camera_session {
    std::shared_ptr<camera> device;
    bool opened = false;
    bool streaming = false;

    int finish() {
        int status = 0;
        if (streaming) {
            const int result = device->stop();
            streaming = false;
            if (result != 0) {
                std::cerr << "Stream-off failed: " << result << '\n';
                status = 1;
            }
        }
        if (opened) {
            const int result = device->close();
            opened = false;
            if (result != 0) {
                std::cerr << "Close failed: " << result << '\n';
                status = 1;
            }
        }
        return status;
    }

    ~camera_session() { finish(); }
};

} // namespace

int main(int argc, char** argv) {
    options opts;
    if (!parse_args(argc, argv, opts)) {
        usage(argv[0]);
        return 2;
    }

    auto& manager = camera_manager::getInstance();
    const int init_result = manager.init();
    if (init_result != 0) {
        std::cerr << "Camera manager initialization failed: " << init_result << '\n';
        return 1;
    }

    const auto cameras = manager.get_camera_list();
    if (cameras.empty()) {
        std::cerr << "No IMX704 camera found\n";
        return 1;
    }
    if (opts.list_only) {
        for (std::size_t i = 0; i < cameras.size(); ++i) {
            std::cout << "Camera #" << i << ": " << cameras[i].id
                      << " (" << cameras[i].model << ")\n";
            for (const auto& mode : cameras[i].supported_modes)
                std::cout << "  Mode: 0x" << std::hex << mode.first << std::dec << '\n';
        }
        return 0;
    }
    if (opts.camera_index >= cameras.size()) {
        std::cerr << "Camera index out of range\n";
        return 2;
    }

    const auto& selected = cameras[opts.camera_index];
    if (selected.supported_modes.find(opts.mode) == selected.supported_modes.end()) {
        std::cerr << "Mode 0x" << std::hex << opts.mode << " is not supported\n";
        return 2;
    }

    camera_session session;
    session.device = manager.get_camera(selected.id);
    if (!session.device) {
        std::cerr << "Could not acquire camera " << selected.id << '\n';
        return 1;
    }
    int result = session.device->open(opts.mode);
    if (result != 0) {
        std::cerr << "Open failed: " << result << '\n';
        return 1;
    }
    session.opened = true;

    camera_output_configuration config{};
    config.enable_point_cloud = true;
    result = session.device->configure_camera_output(config);
    if (result == 0)
        result = session.device->configure_camera_sync_mode(camera_sync_master_mode);
    if (result == 0)
        result = session.device->configure_camera_echo(1);
    if (result != 0) {
        std::cerr << "Configure failed: " << result << '\n';
        return 1;
    }

    result = session.device->start();
    if (result != 0) {
        std::cerr << "Stream-on failed: " << result << '\n';
        return 1;
    }
    session.streaming = true;
    // On Jetson the camera MCU initializes after stream-on, not before it.
    std::this_thread::sleep_for(std::chrono::milliseconds(opts.startup_delay_ms));

    const auto started_at = std::chrono::steady_clock::now();
    unsigned int received = 0;
    for (unsigned int attempt = 0; attempt < opts.frames; ++attempt) {
        const frame_buffer& frame = session.device->get_frame(opts.timeout_ms);
        if (frame.error == -ETIME) {
            std::cerr << "Frame timeout\n";
            continue;
        }
        if (frame.error != 0) {
            std::cerr << "Frame error: " << frame.error << '\n';
            return 1;
        }
        if (frame.point_cloud.empty()) {
            std::cerr << "Frame has no point cloud\n";
            return 1;
        }
        ++received;
        std::cout << "Frame " << received << ": id=" << frame.frame_id
                  << ", points=" << frame.point_cloud[0].size() << '\n';
    }
    const auto elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started_at).count();
    std::cout << "Received " << received << '/' << opts.frames << " frames in "
              << std::fixed << std::setprecision(2) << elapsed << "s ("
              << (elapsed > 0 ? received / elapsed : 0.0) << " FPS)\n";
    const int cleanup_result = session.finish();
    return received == opts.frames && cleanup_result == 0 ? 0 : 1;
}
