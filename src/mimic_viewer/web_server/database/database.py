import configparser
from contextlib import asynccontextmanager
import os

from google.cloud.sql.connector import Connector
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read(os.environ["DB_CONFIG_PATH"])
        self.username = config["db"]["username"]
        self.password = config["db"]["password"]
        self.connection_string = config["db"]["connection_string"]
        self.db_name = config["db"]["db_name"]

        self.connector = Connector()

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection."""
            # Use Cloud SQL Connector
        conn = self.connector.connect(
            instance_connection_string=self.connection_string, 
            driver="pg8000", 
            user=self.username, 
            password=self.password, 
            db=self.db_name
        )
        
        try:
            yield conn
        finally:
            self.connector.close()

    async def get_episode_url(self, episode_id: int):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Query the episodes table to get the URL
            query = """
                SELECT url 
                FROM preproduction.episodes 
                WHERE id = %s
            """
            
            cursor.execute(query, (episode_id,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                return None
    
    async def get_episode_info(self, episode_id: int):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Query to get episode info with subdataset details
            query = """
                SELECT 
                    e.id,
                    e.url,
                    e.uploaded_at,
                    s.name as subdataset_name,
                    s.description as subdataset_description,
                    emb.name as embodiment_name,
                    tm.name as teleop_mode_name
                FROM preproduction.episodes e
                LEFT JOIN preproduction.subdatasets s ON e.subdataset_id = s.id
                LEFT JOIN preproduction.embodiments emb ON s.embodiment_id = emb.id
                LEFT JOIN preproduction.teleop_modes tm ON s.teleop_mode_id = tm.id
                WHERE e.id = %s
            """
            
            cursor.execute(query, (episode_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "id": result[0],
                    "url": result[1],
                    "uploaded_at": result[2],
                    "subdataset_name": result[3],
                    "subdataset_description": result[4],
                    "embodiment_name": result[5],
                    "teleop_mode_name": result[6],
                }
            else:
                return None
    
# Global database manager instance
db_manager = DatabaseManager()