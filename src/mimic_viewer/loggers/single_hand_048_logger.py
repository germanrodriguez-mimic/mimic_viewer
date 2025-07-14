import math
import numpy as np
from mimic_viewer.loggers.embodiment_logger import EmbodimentLogger
import rerun as rr
from rerun_loader_urdf import URDFLogger
from scipy.spatial.transform import Rotation as R

from mimic_viewer.loggers.utils import HandJointsLoggingInfo, ImageLoggingInfo, WristPoseLoggingInfo, log_base_transform, log_joint_transform

class SingleHand048Logger(EmbodimentLogger):
    def __init__(self, urdf_path, recording = None):
        super().__init__(urdf_path, recording)
        self.__hand_urdf_path = self.urdf_path + "/p48/converted.urdf"
        hand_logger = URDFLogger(
            self.__hand_urdf_path, 
            entity_path_prefix="/world/base/hand"
        )
        for material in hand_logger.urdf.materials:
            material.color.rgba = [0,0.6,0,0.6] # green

        camera_topics = [
            "cameras__fixed_0",
            "cameras__wrist_top",
            "cameras__wrist_bottom"
        ]

        self.wrist_pose_logging_infos.append(
            WristPoseLoggingInfo(
                "mimic__right__root__commanded_pose",
                "/world/base/hand",
                # the hand urdfs are rotated 180 degrees at their mount point
                np.array([0,0,180])
            )
        )

        for topic in camera_topics:
            replaced_topic = topic.replace("__", "/")
            self.image_logging_infos.append(
                ImageLoggingInfo(
                    topic,
                    replaced_topic
                )
            )

        self.hand_joint_logging_infos.append(
            HandJointsLoggingInfo(
                "mimic_hand__right__joint_cmd",
                hand_logger,
                self.__filter_actionable_joints(hand_logger),
                self.__filter_joint_offsets(hand_logger),
                self.__filter_follower_joints(hand_logger),
            )
        )

    def reset(self):
        super().reset()
        identity_rotation = R.from_matrix(np.eye(3))
        log_base_transform("/world", np.zeros((0,3)), identity_rotation, recording=self.recording)

    def __filter_actionable_joints(self, logger):
        """
        Excludes joints containing "offset", "root", or "dp" (unless "thumb" is also present).
        """
        all_joints = [joint for joint in logger.urdf.joints]
        filtered = []
        for joint in all_joints:
            if "offset" in joint.name:
                continue
            if "root" in joint.name:
                continue
            if "dp" in joint.name and "thumb" not in joint.name:
                continue
            filtered.append(joint)
        return filtered

    def __filter_joint_offsets(self, logger):
        joint_offsets_rule = {
            'thumb_base2cmc': 30.0,
            'thumb_cmc2mcp': -55.0,
            'thumb_mcp2pp': 40.0,
            'thumb_pp2dp_actuated': 40.0,
            'index_base2mcp': 8.5,
            'index_mcp2pp': 15.0,
            'index_pp2mp': 15.0,
            'middle_base2mcp': 12.5,
            'middle_mcp2pp': 15.0,
            'middle_pp2mp': 15.0,
            'ring_base2mcp': 17.5,
            'ring_mcp2pp': 15.0,
            'ring_pp2mp': 15.0,
            'pinky_base2mcp': 22.5,
            'pinky_mcp2pp': 15.0,
            'pinky_pp2mp': 15.0,
        }
        name_to_joint = {joint.name: joint for joint in logger.urdf.joints}
        offsets_map = {name_to_joint[name]: value for name, value in joint_offsets_rule.items()}
        return offsets_map

    def __filter_follower_joints(self, logger):
        follower_joints_rule = {
            'index_pp2mp': 'index_mp2dp',
            'middle_pp2mp':'middle_mp2dp',
            'ring_pp2mp':  'ring_mp2dp',
            'pinky_pp2mp': 'pinky_mp2dp'
        }
        name_to_joint = {joint.name: joint for joint in logger.urdf.joints}
        joint_to_follower_joint_map = {
            name_to_joint[src]: name_to_joint[dst]
            for src, dst in follower_joints_rule.items()
            if src in name_to_joint and dst in name_to_joint
        }
        return joint_to_follower_joint_map

    def set_blueprint(self):
        blueprint = rr.blueprint.Horizontal(
            rr.blueprint.Spatial3DView(name="robot view", origin="/", contents=["/**"]),
            rr.blueprint.Vertical(
                rr.blueprint.Spatial2DView(name="Fixed", origin="cameras/fixed_0"),
                rr.blueprint.Horizontal(
                    rr.blueprint.Spatial2DView(name="Wrist top", origin="cameras/wrist_top"),
                    rr.blueprint.Spatial2DView(name="Wrist bottom", origin="cameras/wrist_bottom"),
                ),
            ),
            rr.blueprint.SelectionPanel(state="collapsed"),
            rr.blueprint.BlueprintPanel(state="collapsed"),
            rr.blueprint.TimePanel(state="collapsed"),
            column_shares=[0.5,0.5],
        )
        self.recording.send_blueprint(blueprint)
