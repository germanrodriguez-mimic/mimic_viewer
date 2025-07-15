from collections.abc import Generator
import numpy as np

class ZarrPointLoader:
    def __init__(self, zarr_root):
        self.__root = zarr_root
        self.__data_group_names = []
        self.__group_lengths = {}

        for name in self.__root.array_keys():
            if not name.endswith('_timestamps'):
                timestamp_name = f"{name}_timestamps"
                if timestamp_name in self.__root.array_keys():
                    data_array = self.__root[name]
                    timestamp_array = self.__root[timestamp_name]
                    if len(data_array) == len(timestamp_array):
                        self.__data_group_names.append(name)
                        self.__group_lengths[name] = len(data_array)
                else:
                    print(f"Warning: Data group '{name}' found, but no corresponding timestamp group '{timestamp_name}'. Skipping.")
            else:
                pass

        self.__data_group_names.sort()

    def get_data(self) -> Generator[tuple[str, float, np.ndarray], None, None]:
        """
        This method goes through every available data group of the zarr.
        There are two types of group, "data groups" and "timestamp groups", for every data group,
        there exists a corresponding timestamp group with the same name and length and the _timestamps suffix.
        When called, this method yields a tuple of (data group name, timestamp, value). when it first needs data
        from a new chunk, it loads the entire chunk at once and keeps it in memory in order to prevent slow 
        calls to the zarr filesystem. it goes through the first index of every data group, then the second index,
        and so on until all groups are done at which point it returns
        """
        if not self.__data_group_names:
            return

        chunk_sizes = {name: self.__root[name].chunks[0] for name in self.__data_group_names}

        # Caches to hold the currently loaded chunk for each group.
        # The key is the group name, and the value is a tuple of (chunk_index, chunk_data).
        data_chunk_cache = {}
        timestamp_chunk_cache = {}

        # Find the length of the longest group to define the global iteration range.
        max_len = max(self.__group_lengths.values()) if self.__group_lengths else 0

        # --- 2. Iteration ---
        # Iterate from the first to the last index across all groups.
        for i in range(max_len):
            # For each index, loop through the data groups to maintain the required yield order.
            for name in self.__data_group_names:

                # Process only if the index `i` is valid for the current group.
                if i < self.__group_lengths[name]:
                    chunk_size = chunk_sizes[name]
                    
                    # --- 3. Chunk Management ---
                    # Calculate which chunk is needed for the current index `i`.
                    required_chunk_idx = i // chunk_size
                    current_chunk_idx = data_chunk_cache.get(name, (-1, None))[0]

                    # If the required chunk is not the one in memory, load it.
                    if required_chunk_idx != current_chunk_idx:
                        # Define the slice for reading the new chunk from Zarr.
                        chunk_start = required_chunk_idx * chunk_size
                        chunk_end = min(chunk_start + chunk_size, self.__group_lengths[name])
                        
                        # Load the new data and timestamp chunks into the caches.
                        data_chunk_cache[name] = (required_chunk_idx, self.__root[name][chunk_start:chunk_end])
                        timestamp_chunk_cache[name] = (required_chunk_idx, self.__root[f"{name}_timestamps"][chunk_start:chunk_end])

                    # --- 4. Yield Data ---
                    # Calculate the index of the data point within the cached chunk.
                    index_in_chunk = i % chunk_size
                    
                    # Retrieve the value and timestamp from the in-memory chunks.
                    value = data_chunk_cache[name][1][index_in_chunk]
                    timestamp = timestamp_chunk_cache[name][1][index_in_chunk]

                    yield name, timestamp, value