from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from mimic_viewer.data_sources.zarr_batch_loader import ZarrBatchLoader
import uvicorn
import os
import random

import zarr
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import rerun as rr
from ament_index_python.packages import get_package_share_directory

from mimic_viewer.loggers.bimanual_049_logger import Bimanual049Logger
from mimic_viewer.loggers.single_hand_048_logger import SingleHand048Logger
from mimic_viewer.web_server.database.database import db_manager
from mimic_viewer.web_server.recordings.recording_manager import RecordingData, RecordingDataManager

load_dotenv()

MAX_RECORDINGS = int(os.environ["MAX_RECORDINGS"])
ZARR_DATA_LOADING_LIMIT = int(os.environ["ZARR_DATA_LOADING_LIMIT"])
SERVER_IP_ADDRESS = os.environ["SERVER_IP_ADDRESS"]
recording_data_manager = RecordingDataManager(max_size=MAX_RECORDINGS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global recording_data_manager
    # startup
    rr.serve_web_viewer(web_port=9000, open_browser=False)
    yield
    # cleanup
    recording_data_manager.cleanup_all()

def get_rerun_json_response(port):
    return JSONResponse(
        content={
            "url": f"rerun://{SERVER_IP_ADDRESS}:{port}/proxy"
        }
    )

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Specifies the allowed origins
    allow_credentials=True,      # Allows cookies to be included in requests
    allow_methods=["*"],         # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],         # Allows all request headers
)

def log_episode_background_task(logger, episode_url):
    logger.log_text(episode_url)
    logger.log_text("Loading zarr data...", level=rr.TextLogLevel.WARN)
    root = zarr.open(episode_url)
    data_loader = ZarrBatchLoader(root).get_data(ZARR_DATA_LOADING_LIMIT)
    for index, data in enumerate(data_loader):
        logger.log_data_batches(data)
        logger.log_text(f"Logged data batch #{index + 1}")
    logger.log_text("All data has been logged!")



@app.get("/log_episode")
async def log_episode(episode_id: int, background_tasks: BackgroundTasks):
    global recording_data_manager
    
    episode_recording_data = recording_data_manager.find_by_episode_id(episode_id)

    if episode_recording_data is not None:
        return get_rerun_json_response(episode_recording_data.grpc_port)
 
    episode_info = await db_manager.get_episode_info(episode_id)
    if not episode_info:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    episode_url = episode_info["url"]
    if not episode_url:
        raise HTTPException(status_code=404, detail="Episode URL not found")
    
    # Determine if it's bimanual based on embodiment name
    is_bimanual = "bimanual" in episode_info.get("embodiment_name", "").lower()

    new_recording = rr.RecordingStream(f"viewing_{episode_id}")
    
    grpc_port = 0
    while grpc_port < 9000 or recording_data_manager.is_port_used(grpc_port):
        grpc_port = random.randint(9001, 65535)
    
    new_recording.serve_grpc(grpc_port=grpc_port, server_memory_limit="90%")
    
    pkg_share_path = get_package_share_directory("mimic_viz")
    urdfs_path = f"{pkg_share_path}/urdf"
    logger = Bimanual049Logger(urdfs_path, new_recording) if is_bimanual else SingleHand048Logger(urdfs_path, new_recording)
    logger.reset()

    new_episode_recording_data = RecordingData(
        episode_id=episode_id,
        recording=new_recording,
        grpc_port=grpc_port
    )

    recording_data_manager.add(new_episode_recording_data)

    background_tasks.add_task(log_episode_background_task, logger, episode_url)

    return get_rerun_json_response(grpc_port)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    