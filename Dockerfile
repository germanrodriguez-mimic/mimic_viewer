# syntax=docker/dockerfile:1

FROM ros:humble AS cloner

RUN apt-get update && apt-get install -y --no-install-recommends \
    git rsync \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /robotics
RUN --mount=type=secret,id=netrc-secret,target=/root/.netrc \
    git clone https://github.com/mimicrobotics/mimic_robotics.git && \
    cd mimic_robotics && git checkout tmp/bimanual-inference

RUN rsync -av --progress /robotics/mimic_robotics/ros_packages/utils/mimic_viz/ /mimic_viz --exclude urdf --exclude meshes \
    && rsync -av --progress /robotics/mimic_robotics/utils/mimic_hand_middleware/mimic_hand_middleware/hand_definitions/urdf /mimic_viz/

RUN find /mimic_viz -type f -exec sed -i 's#mimic_viz/meshes/p49#mimic_viz/urdf/p49#g' {} +

FROM ros:humble

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG=en_US.utf8

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-rosdep \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

RUN source /opt/ros/humble/setup.bash && rosdep update

WORKDIR /workspace/mimic_viewer
COPY . .

RUN pip install -e ".[web]"

COPY --from=cloner /mimic_viz /robotics/share/mimic_viz

RUN mkdir -p /robotics/share/ament_index/resource_index/packages \
    && touch /robotics/share/ament_index/resource_index/packages/mimic_viz

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc

CMD ["bash"]