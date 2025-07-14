import rerun as rr

from mimic_viewer.loggers.utils import EffortsLoggingInfo, HandJointsLoggingInfo, ImageLoggingInfo, WristPoseLoggingInfo, log_efforts_batch, log_hand_joints, log_hand_joints_batch, log_image, log_image_batch, log_wrist_pose, log_wrist_pose_batch

class EmbodimentLogger:
    def __init__(self, urdf_path, recording):
        self.urdf_path = urdf_path
        self.recording : rr.RecordingStream = recording
        self.image_logging_infos : list[ImageLoggingInfo] = []
        self.hand_joint_logging_infos : list[HandJointsLoggingInfo] = []
        self.wrist_pose_logging_infos : list[WristPoseLoggingInfo] = []
        self.efforts_logging_infos : list[EffortsLoggingInfo] = []

    def set_blueprint(self):
        pass

    def set_time(self, time):
        self.recording.set_time("time", duration=time)

    def reset(self):
        self.recording.log("", rr.Clear(recursive=True))
        self.set_blueprint()
        self.set_time(0)
        self.recording.log("/", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
        for hand_joint_logging_info in self.hand_joint_logging_infos:
            hand_joint_logging_info.logger.log(self.recording)

    def log_text(self, text, level=rr.TextLogLevel.INFO):
        print(f"[{level.name}]: {text}")
        self.recording.log("logs", rr.TextLog(text, level=level))

    def log_data_point(self, data_point):
        """
        data_point is a tuple of (topic_name, timestamp_ns, value)
        """
        key, ts, value = data_point
        self.set_time(ts / 1e9)

        for image_logging_info in self.image_logging_infos:
            if image_logging_info.topic_name == key:
                log_image(image_logging_info.entity_name, value, self.recording)
                return
        
        for hand_joint_logging_info in self.hand_joint_logging_infos:
            if hand_joint_logging_info.topic_name == key:
                log_hand_joints(hand_joint_logging_info, value, self.recording)
                return
            
        for wrist_pose_logging_info in self.wrist_pose_logging_infos:
            if wrist_pose_logging_info.topic_name == key:
                log_wrist_pose(wrist_pose_logging_info, value, self.recording)
                return
    
    def log_data_batches(self, data_batches):
        """
        data_batch is a list of dictionary where each dict has topic_name,
        values, and timestamps keys 
        """
        for topic_batch in data_batches:
            key = topic_batch["topic_name"]
            values = topic_batch["values"]
            timestamps = topic_batch["timestamps"]

            for wrist_pose_logging_info in self.wrist_pose_logging_infos:
                if wrist_pose_logging_info.topic_name == key:
                    log_wrist_pose_batch(wrist_pose_logging_info, values, timestamps, self.recording)

            for hand_joint_logging_info in self.hand_joint_logging_infos:
                if hand_joint_logging_info.topic_name == key:
                    log_hand_joints_batch(hand_joint_logging_info, values, timestamps, self.recording)

            for image_logging_info in self.image_logging_infos:
                if image_logging_info.topic_name == key:
                    log_image_batch(image_logging_info.entity_name, values, timestamps, self.recording)
            
            for efforts_logging_info in self.efforts_logging_infos:
                if efforts_logging_info.topic_name == key:
                    log_efforts_batch(efforts_logging_info, values, timestamps, self.recording)

            

            