cmake_minimum_required(VERSION 3.10)
project(ohrc_hw_config)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
 config
 DESTINATION share/${PROJECT_NAME}
)

ament_package()