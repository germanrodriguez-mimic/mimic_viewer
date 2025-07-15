# Mimic Viewer

Visualize Robot Data with Rerun.

## How to use

### I want to see episodes from the website

1. Install the local viewer

```bash
./install_local_viewer/linux/install.sh # or  ./install_local_viewer/macos/install.sh
```

2. Click an episode from the website, a rerun window should open and data will soon be logged to it.

### Use case: I want to log data in real time

1. Install the project in your environment

```bash
pip install .
```

2. Instantiate the logger

```python
from mimic_viewer.loggers.bimanual_049_logger import Bimanual049Logger
import rerun as rr
import numpy as np
import time

rr.init("log_data_in_real_time")

logger = Bimanual049Logger("path/to/robot/urdfs", rr.get_global_data_recording())
logger.reset()

logger.log_text("hello")

# the log_data method expects a (key, timestamp_ns, value) tuple
image = np.random.randint(0, 256, (240, 240, 3), dtype=np.uint8)
timestamp = time.time_ns()

logger.log_data(("cameras__fixed_0", timestamp, image))
```

Coming soon: ROS Data Source to automatically subscribe to topics and forward the data to logger

### Use case: I want to log data from a zarr episode

If the episode is available locally:

```python
from mimic_viewer.loggers.bimanual_049_logger import Bimanual049Logger
from mimic_viewer.data_sources.zarr_batch_loader import ZarrBatchLoader
import zarr
import rerun as rr

rr.init("log_data_from_zarr")

logger = Bimanual049Logger("path/to/robot/urdfs", rr.get_global_data_recording())
logger.reset()

logger.log_text("hello")

root = zarr.open("/path/to/zarr")
loader = ZarrBatchLoader(root)

indices_per_log_call = 1000
for data_batch in loader.get_data(indices_per_log_call):
    logger.log_data_batches(data_batch)
```

If the episode is in the cloud you'll need a few extra dependencies

```bash
pip install ".[web]"
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json"
```

Then you can open zarrs from the bucket

```python
from mimic_viewer.loggers.bimanual_049_logger import Bimanual049Logger
from mimic_viewer.data_sources.zarr_batch_loader import ZarrBatchLoader
import zarr
import rerun as rr

rr.init("log_data_from_zarr")

logger = Bimanual049Logger("path/to/robot/urdfs", rr.get_global_data_recording())
logger.reset()

logger.log_text("hello")

root = zarr.open("gs://path/to/zarr/in/bucket")
loader = ZarrBatchLoader(root)

indices_per_log_call = 1000
for data_batch in loader.get_data(indices_per_log_call):
    logger.log_data_batches(data_batch)
```

### Use case: I want to start the viewer server

1. Build the docker image

```bash
./build.sh
```

2. Create a .env file

```bash
SERVER_IP_ADDRESS="0.0.0.0"
MAX_RECORDINGS="3"
DEBUG="False"
# these two should always have these values since they are mounted in the container
GOOGLE_APPLICATION_CREDENTIALS="/.auth/cloud/gcp/service-account-key.json"
DB_CONFIG_PATH="/.auth/db_config.ini"
```

3. Launch

```bash
docker compose up
```