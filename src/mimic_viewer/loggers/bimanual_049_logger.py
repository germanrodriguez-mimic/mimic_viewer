import itertools
import numpy as np
from mimic_viewer.loggers.embodiment_logger import EmbodimentLogger
import rerun as rr
from rerun_loader_urdf import URDFLogger
from scipy.spatial.transform import Rotation as R

from mimic_viewer.loggers.utils import EffortsLoggingInfo, HandJointsLoggingInfo, ImageLoggingInfo, WristPoseLoggingInfo, log_base_transform, log_image, log_joint_transform

class Bimanual049Logger(EmbodimentLogger):
    def __init__(self, urdf_path, recording = None):
        super().__init__(urdf_path, recording)

        self.__actionable_joint_names = [
            'thumb_base2cmc',
            'thumb_cmc2mcp',
            'thumb_mcp2pp',
            'thumb_pp2dp_actuated',
            'index_base2mcp',
            'index_mcp2pp',
            'index_pp2mp',
            'middle_base2mcp',
            'middle_mcp2pp',
            'middle_pp2mp',
            'ring_base2mcp',
            'ring_mcp2pp',
            'ring_pp2mp',
            'pinky_base2mcp',
            'pinky_mcp2pp',
            'pinky_pp2mp',
        ]
   
        right_hand_urdf_path = self.urdf_path + "/p49/converted.urdf"
        left_hand_urdf_path = self.urdf_path + "/p49l/converted.urdf"
        
        left_hand_logger = URDFLogger(
            left_hand_urdf_path, 
            entity_path_prefix="/world/left/base/hand"
        )
        right_hand_logger = URDFLogger(
            right_hand_urdf_path, 
            entity_path_prefix="/world/right/base/hand"
        )
        for material in itertools.chain(
            left_hand_logger.urdf.materials,
            right_hand_logger.urdf.materials,
        ):
            material.color.rgba = [0,0.6,0,0.6] # green
        
        self.hand_joint_logging_infos.extend(
            [
                HandJointsLoggingInfo(
                    "mimic_hand__left__joint_cmd",
                    left_hand_logger,
                    self.__filter_actionable_joints(left_hand_logger),
                    self.__filter_joint_offsets(left_hand_logger),
                    self.__filter_follower_joints(left_hand_logger),

                ),
                HandJointsLoggingInfo(
                    "mimic_hand__right__joint_cmd",
                    right_hand_logger,
                    self.__filter_actionable_joints(right_hand_logger),
                    self.__filter_joint_offsets(right_hand_logger),
                    self.__filter_follower_joints(right_hand_logger),
                ),
            ]
        )

        left_hand_proprio_logger = URDFLogger(
            left_hand_urdf_path, 
            entity_path_prefix="/world/left/base/hand_proprio"
        )
        right_hand_proprio_logger = URDFLogger(
            right_hand_urdf_path, 
            entity_path_prefix="/world/right/base/hand_proprio"
        )
        
        self.hand_joint_logging_infos.extend(
            [
                HandJointsLoggingInfo(
                    "mimic_hand__left__proprioceptive_state_positions",
                    left_hand_proprio_logger,
                    self.__filter_proprio_joints(left_hand_proprio_logger),
                    in_radians=True,
                ),
                HandJointsLoggingInfo(
                    "mimic_hand__right__proprioceptive_state_positions",
                    right_hand_proprio_logger,
                    self.__filter_proprio_joints(right_hand_proprio_logger),
                    in_radians=True,
                ),
            ]
        )

        self.efforts_logging_infos.append(
            EffortsLoggingInfo(
                "mimic_hand__right__motors_state_efforts",
                "motors",
                lambda joint_index: f"/{self.__actionable_joint_names[joint_index]}/effort"
            )
        )

        camera_topics = [
            "cameras__fixed_0",
            "cameras__left__wrist_top",
            "cameras__right__wrist_top",
            "cameras__left__wrist_bottom",
            "cameras__right__wrist_bottom"
        ]

        for topic in camera_topics:
            replaced_topic = topic.replace("__", "/")
            self.image_logging_infos.append(
                ImageLoggingInfo(
                    topic,
                    replaced_topic
                )
            )

        self.wrist_pose_logging_infos.extend(
            [
                WristPoseLoggingInfo(
                    "mimic__right__root__state_pose",
                    "/world/right/base/hand_proprio",
                    # the hand urdfs are rotated 180 degrees at their mount point
                    np.array([0,0,180])
                ),
                WristPoseLoggingInfo(
                    "mimic__left__root__state_pose",
                    "/world/left/base/hand_proprio",
                    # the hand urdfs are rotated 180 degrees at their mount point
                    np.array([0,0,180])
                ),
                WristPoseLoggingInfo(
                    "mimic__right__root__commanded_pose",
                    "/world/right/base/hand",
                    # the hand urdfs are rotated 180 degrees at their mount point
                    np.array([0,0,180])
                ),
                WristPoseLoggingInfo(
                    "mimic__left__root__commanded_pose",
                    "/world/left/base/hand",
                    # the hand urdfs are rotated 180 degrees at their mount point
                    np.array([0,0,180])
                ),
            ]
        )
        
    
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

    
    def __filter_proprio_joints(self, logger):
        """
        Excludes joints containing "offset", "root"
        """
        all_joints = [joint for joint in logger.urdf.joints]
        filtered = []
        for joint in all_joints:
            if "offset" in joint.name:
                continue
            if "root" in joint.name:
                continue
            filtered.append(joint)
        return filtered

    def reset(self):
        super().reset()
        identity_rotation = R.from_matrix(np.eye(3))
        log_base_transform("/world", np.zeros((0,3)), identity_rotation, recording=self.recording)
        log_base_transform("/world/right/base", [0,-0.29,0],identity_rotation, recording=self.recording)
        log_base_transform("/world/left/base", [0,0.29,0],identity_rotation, recording=self.recording)

    def set_blueprint(self):
        blueprint=rr.blueprint.Tabs(
                rr.blueprint.Horizontal(
                    rr.blueprint.Spatial3DView(name="robot view", origin="/", contents=["/**"]),
                    rr.blueprint.Vertical(
                        rr.blueprint.Spatial2DView(name="fixed", origin="cameras/fixed_0"),
                        rr.blueprint.Horizontal(
                            rr.blueprint.Spatial2DView(name="left top", origin="cameras/left/wrist_top"),
                            rr.blueprint.Spatial2DView(name="left bottom", origin="cameras/left/wrist_bottom"),
                        ),
                        rr.blueprint.Horizontal(
                            rr.blueprint.Spatial2DView(name="right top", origin="cameras/right/wrist_top"),
                            rr.blueprint.Spatial2DView(name="right bottom", origin="cameras/right/wrist_bottom"),
                        ),
                        name="cameras",
                        row_shares=[0.5,0.25,0.25],
                    ),
                    rr.blueprint.SelectionPanel(state="collapsed"),
                    rr.blueprint.BlueprintPanel(state="collapsed"),
                    rr.blueprint.TimePanel(state="collapsed"),
                    column_shares=[0.5,0.5],
                    name="simple view"
                ),
                rr.blueprint.Horizontal(
                    rr.blueprint.Vertical(
                        rr.blueprint.Spatial3DView(name="robot view", origin="/", contents=["/**"]),
                        rr.blueprint.Grid(
                            name="motor efforts", 
                            grid_columns=4,
                            contents=[
                                rr.blueprint.TimeSeriesView(name=joint, origin=f"motors/{joint}/effort") for joint in self.__actionable_joint_names
                            ]
                        ),
                        row_shares=[0.5, 0.5]
                    ),
                    rr.blueprint.Vertical(
                        rr.blueprint.Spatial2DView(name="fixed", origin="cameras/fixed_0"),
                        rr.blueprint.Horizontal(
                            rr.blueprint.Spatial2DView(name="left top", origin="cameras/left/wrist_top"),
                            rr.blueprint.Spatial2DView(name="left bottom", origin="cameras/left/wrist_bottom"),
                        ),
                        rr.blueprint.Horizontal(
                            rr.blueprint.Spatial2DView(name="right top", origin="cameras/right/wrist_top"),
                            rr.blueprint.Spatial2DView(name="right bottom", origin="cameras/right/wrist_bottom"),
                        ),
                        name="cameras",
                    ),
                    rr.blueprint.SelectionPanel(state="collapsed"),
                    rr.blueprint.BlueprintPanel(state="collapsed"),
                    rr.blueprint.TimePanel(state="collapsed"),
                    column_shares=[0.6,0.4],
                    name="detailed view"
                )
        )
        self.recording.send_blueprint(blueprint)
