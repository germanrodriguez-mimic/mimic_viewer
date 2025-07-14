from dataclasses import dataclass, field
import datetime
import rerun as rr

@dataclass
class RecordingData:
    episode_id: int
    recording: rr.RecordingStream
    grpc_port: int
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)

class RecordingDataManager:
    def __init__(self, max_size):
        if max_size <= 0:
            raise ValueError("Max size must be a positive integer.")
        self.max_size = max_size
        self._recordings: dict[int, RecordingData] = {}
        self._used_ports: set[int] = set()

    def add(self, new_data: RecordingData):
        if new_data.episode_id in self._recordings:
            print(f"⚠️ Warning: Episode ID '{new_data.episode_id}' already exists. Ignoring.")
            return

        if new_data.grpc_port in self._used_ports:
            print(f"⚠️ Warning: gRPC port {new_data.grpc_port} is already in use. Ignoring.")
            return

        if len(self._recordings) >= self.max_size:
            print(f"🗑️ Capacity reached. Evicting oldest recording.")
            self._evict_oldest()

        # Add the new recording data
        self._recordings[new_data.episode_id] = new_data
        self._used_ports.add(new_data.grpc_port)
        print(f"➕ Added recording for episode '{new_data.episode_id}' on port {new_data.grpc_port}.")

    def find_by_episode_id(self, episode_id: str) -> RecordingData | None:
        return self._recordings.get(episode_id)

    def is_port_used(self, port: int) -> bool:
        return port in self._used_ports

    def _cleanup(self, data_to_remove: RecordingData):
        data_to_remove.recording.disconnect()
        self._used_ports.remove(data_to_remove.grpc_port)

    def cleanup_all(self):
        if not self._recordings:
            print("Manager is already empty. No cleanup needed.")
            return

        print(f"✨ Applying cleanup to all {len(self._recordings)} recordings...")
        all_episode_ids = list(self._recordings.keys())
        for episode_id in all_episode_ids:
            if episode_id in self._recordings:
                data_to_remove = self._recordings.pop(episode_id)
                self._cleanup(data_to_remove)
        
        print("✅ All recordings have been cleaned up and removed.")

    def _evict_oldest(self):
        if not self._recordings:
            return
        oldest_data = min(self._recordings.values(), key=lambda data: data.created_at)
        self._recordings.pop(oldest_data.episode_id)
        self._cleanup(oldest_data)

    def __len__(self):
        return len(self._recordings)