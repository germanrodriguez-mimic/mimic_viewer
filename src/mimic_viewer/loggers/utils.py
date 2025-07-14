from collections.abc import Callable
from dataclasses import dataclass, field
import math
import numpy as np
import rerun as rr
from scipy.spatial.transform import Rotation as R
from rerun_loader_urdf import URDFLogger
from urdf_parser_py.urdf import Joint

JOINT_TRANSFORM_AXIS_SIZE = 0.02
BASE_TRANSFORM_AXIS_SIZE = 0.06

@dataclass
class HandJointsLoggingInfo:
    topic_name : str
    logger : URDFLogger
    actionable_joints : list[Joint]
    joint_to_offset_map: dict[Joint, float] = field(default_factory = dict)
    joint_to_follower_joint_map: dict[Joint, Joint] = field(default_factory = dict)
    in_radians : bool = False

@dataclass
class WristPoseLoggingInfo:
    topic_name: str
    entity_name: str
    additional_rotation: np.ndarray

@dataclass
class EffortsLoggingInfo:
    topic_name: str
    entity_name: str
    suffix_generator: Callable

@dataclass
class ImageLoggingInfo:
    topic_name: str
    entity_name: str
    color_model: str = "BGR"

def log_transform(entity, translation_vector, rotation_object, axis_length, recording):
    rotation_matrix = rotation_object.as_matrix()
    recording.log(entity, rr.Transform3D(translation=translation_vector, mat3x3=rotation_matrix, axis_length=axis_length))

def log_base_transform(entity, translation_vector, rotation_object, recording):
    log_transform(entity, translation_vector, rotation_object, BASE_TRANSFORM_AXIS_SIZE, recording)

def log_joint_transform(entity, translation_vector, rotation_object, recording):
    log_transform(entity, translation_vector, rotation_object, JOINT_TRANSFORM_AXIS_SIZE, recording)

def log_image(entity, image, recording, color_model = "BGR"):
    recording.log(entity, rr.Image(image, color_model=color_model))

def log_hand_joints(hand_joint_logging_info, values, recording):
    if len(values) != len(hand_joint_logging_info.actionable_joints):
        raise ValueError
    for command, joint in zip(values, hand_joint_logging_info.actionable_joints):
        if hand_joint_logging_info.in_radians:
            command = command * 180 / math.pi
        joint_entity = hand_joint_logging_info.logger.joint_entity_path(joint)
        adjusted_command = (command + hand_joint_logging_info.joint_to_offset_map.get(joint, 0.0)) * math.pi / 180
        initial_joint_rotation = R.from_euler("xyz", joint.origin.rpy)
        joint_rotation = initial_joint_rotation * R.from_rotvec(np.array(joint.axis) * adjusted_command) 
        log_joint_transform(joint_entity, joint.origin.xyz, joint_rotation, recording=recording)
        if joint in hand_joint_logging_info.joint_to_follower_joint_map:
            follower_joint = hand_joint_logging_info.joint_to_follower_joint_map[joint]
            follower_joint_entity = hand_joint_logging_info.logger.joint_entity_path(follower_joint)
            log_joint_transform(follower_joint_entity, follower_joint.origin.xyz, joint_rotation, recording=recording)

def log_wrist_pose(wrist_pose_logging_info, value, recording):
    rotation = value[:3,:3]
    translation = value[:3,3]
    additional_rotation = wrist_pose_logging_info.additional_rotation * math.pi / 180
    adjusted_rotation = R.from_matrix(rotation) * R.from_rotvec(additional_rotation)
    log_base_transform(wrist_pose_logging_info.entity_name, translation, adjusted_rotation, recording=recording)

def log_scalar(entity, value, recording):
    recording.log(entity, rr.Scalars(scalars=value))

def log_transform_batch(entity, translation_vectors, rotation_objects, timestamps, axis_length, recording):
    recording.send_columns(
        entity,
        indexes=[rr.TimeColumn("time", duration=timestamps / 1e9)],
        columns=rr.Transform3D.columns(
            translation=translation_vectors,
            quaternion=[rr.Quaternion(xyzw=r.as_quat()) for r in rotation_objects],
            axis_length=[axis_length for _ in timestamps],
        )
    )

def log_base_transform_batch(entity, translation_vectors, rotation_objects, timestamps, recording):
    log_transform_batch(entity, translation_vectors, rotation_objects, timestamps, BASE_TRANSFORM_AXIS_SIZE, recording)

def log_joint_transform_batch(entity, translation_vectors, rotation_objects, timestamps, recording):
    log_transform_batch(entity, translation_vectors, rotation_objects, timestamps, JOINT_TRANSFORM_AXIS_SIZE, recording)

def log_image_batch(entity, values, timestamps, recording, color_model = "BGR"):
    first_image = values[0]
    height = first_image.shape[0]
    width = first_image.shape[1]

    recording.send_columns(
        entity,
        indexes=[rr.TimeColumn("time", duration=timestamps / 1e9)],
        columns=rr.Image.columns(
            buffer = values.view(np.uint8).reshape(len(values), -1),
            format=[rr.components.ImageFormat(
                width=width,
                height=height,
                color_model=color_model,
                channel_datatype="U8"
            )] * len(values)
        )
    )

def log_scalar_batch(entity, values, timestamps, recording):
    recording.send_columns(
        entity, 
        indexes = [rr.TimeColumn("time", duration=timestamps / 1e9)],
        columns = rr.Scalars.columns(scalars=values)
    )

def log_hand_joints_batch(hand_joint_logging_info, values, timestamps, recording):
    num_timestamps, num_joints = values.shape
    if num_joints != len(hand_joint_logging_info.actionable_joints):
        raise ValueError
    if num_timestamps != len(timestamps):
        raise ValueError

    for i, joint in enumerate(hand_joint_logging_info.actionable_joints):
        joint_commands = values[:, i]

        if hand_joint_logging_info.in_radians:
            joint_commands = np.rad2deg(joint_commands)

        offset = hand_joint_logging_info.joint_to_offset_map.get(joint, 0.0)
        adjusted_commands = np.deg2rad(joint_commands + offset)

        translation_vectors = [t for t in np.tile(joint.origin.xyz, (num_timestamps, 1))]

        initial_joint_rotation = R.from_euler("xyz", joint.origin.rpy)
        joint_axis = np.array(joint.axis) # Shape: (3,)
        
        rotation_list = []
        for j in range(num_timestamps):
            single_rotation = initial_joint_rotation * R.from_rotvec(joint_axis * adjusted_commands[j])
            rotation_list.append(single_rotation)
        
        joint_entity = hand_joint_logging_info.logger.joint_entity_path(joint)
        log_joint_transform_batch(
            entity=joint_entity,
            translation_vectors=translation_vectors,
            rotation_objects=rotation_list,
            timestamps=timestamps,
            recording=recording
        )

        if joint in hand_joint_logging_info.joint_to_follower_joint_map:
            follower_joint = hand_joint_logging_info.joint_to_follower_joint_map[joint]
            follower_joint_entity = hand_joint_logging_info.logger.joint_entity_path(follower_joint)
            follower_translation_vectors = [t for t in np.tile(follower_joint.origin.xyz, (num_timestamps, 1))]
            log_joint_transform_batch(
                entity=follower_joint_entity,
                translation_vectors=follower_translation_vectors,
                rotation_objects=rotation_list,
                timestamps=timestamps,
                recording=recording
            )

def log_wrist_pose_batch(wrist_pose_logging_info, values, timestamps, recording):
    if values.ndim != 3 or values.shape[1:] != (4, 4):
        raise ValueError
    
    num_timestamps = values.shape[0]
    if num_timestamps != len(timestamps):
        raise ValueError

    rotation_matrices = values[:, :3, :3]  # Shape: (T, 3, 3)
    translations_array = values[:, :3, 3]   # Shape: (T, 3)

    additional_rotation_rad = wrist_pose_logging_info.additional_rotation * math.pi / 180
    additional_rotation_object = R.from_rotvec(additional_rotation_rad)

    initial_rotations = R.from_matrix(rotation_matrices)
    adjusted_rotations = initial_rotations * additional_rotation_object

    translations = [t for t in translations_array]
    rotations = [r for r in adjusted_rotations]

    log_base_transform_batch(
        entity=wrist_pose_logging_info.entity_name,
        translation_vectors=translations,
        rotation_objects=rotations,
        timestamps=timestamps,
        recording=recording
    )

def log_efforts_batch(efforts_logging_info, values, timestamps, recording):
    num_timestamps, num_joints = values.shape
    if num_timestamps != len(timestamps):
        raise ValueError

    for joint_index in range(num_joints):
        single_joint_slice = values[:, joint_index]
        log_scalar_batch(f"{efforts_logging_info.entity_name}{efforts_logging_info.suffix_generator(joint_index)}", single_joint_slice, timestamps, recording)