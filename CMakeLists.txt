cmake_minimum_required(VERSION 3.18)
project(imx704_jetson_demo LANGUAGES CXX)

set(IMX704_SDK_ROOT "" CACHE PATH "IMX704 C++ SDK installation prefix")

find_path(IMX704_INCLUDE_DIR
    NAMES imx704_camera/camera_manager.h
    HINTS "${IMX704_SDK_ROOT}/include"
)
find_library(IMX704_CAMERA_LIBRARY
    NAMES imx704_camera
    HINTS "${IMX704_SDK_ROOT}/lib" "${IMX704_SDK_ROOT}/lib/aarch64-linux-gnu"
)

if(NOT IMX704_INCLUDE_DIR OR NOT IMX704_CAMERA_LIBRARY)
    message(FATAL_ERROR "IMX704 C++ development library not found. Set -DIMX704_SDK_ROOT=<install-prefix> or install libimx704-dev.")
endif()

find_package(Threads REQUIRED)
find_package(OpenGL REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLFW3 REQUIRED IMPORTED_TARGET glfw3)
add_executable(imx704_cpp_demo cpp/main.cpp cpp/live_display.cpp)
target_compile_features(imx704_cpp_demo PRIVATE cxx_std_17)
target_include_directories(imx704_cpp_demo PRIVATE "${IMX704_INCLUDE_DIR}")
target_link_libraries(imx704_cpp_demo PRIVATE "${IMX704_CAMERA_LIBRARY}" Threads::Threads OpenGL::GL PkgConfig::GLFW3)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(imx704_cpp_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()
