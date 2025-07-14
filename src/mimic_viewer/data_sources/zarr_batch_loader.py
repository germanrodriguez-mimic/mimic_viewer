from collections.abc import Generator

class ZarrBatchLoader:
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

    def get_data(self, batch_size) -> Generator[list[dict], None, None]:
        """
        This method goes through every available data group of the zarr.
        There are two types of group, "data groups" and "timestamp groups", for every data group,
        there exists a corresponding timestamp group with the same name and length and the _timestamps suffix.
        When called, this method yields and array. Each element of the array is a dictionary. the 
        dictionary has a topic_name field (the name of the data group), values (the values from 
        current_index to current_index + batch_size - 1 of that datagroup), timestamps (the corresponding
        timestamps for each data group).
        the next yield gives the next batch next time and so on until the whole zarr is traversed, at which point it breaks.
        It handles data groups of different length by not returning a dictionary if its value array would be empty.
        """
        if not self.__data_group_names:
            return

        current_group_indices = {name: 0 for name in self.__data_group_names}

        while True:
            batch_data = []
            for group_name in self.__data_group_names:
                start_idx = current_group_indices[group_name]
                group_length = self.__group_lengths[group_name]

                if start_idx < group_length:
                    end_idx = start_idx + batch_size
                    actual_end_idx = min(end_idx, group_length)

                    data_array = self.__root[group_name]
                    timestamp_array = self.__root[f"{group_name}_timestamps"]
                    values = data_array[start_idx:actual_end_idx]
                    timestamps = timestamp_array[start_idx:actual_end_idx]

                    batch_data.append({
                        "topic_name": group_name,
                        "values": values,
                        "timestamps": timestamps
                    })

                    current_group_indices[group_name] = actual_end_idx

            if not batch_data:
                break
            
            yield batch_data