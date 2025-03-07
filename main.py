# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import random
import datetime
import uvicorn
import os
from typing import List

origins = [
    "*",  # Allow all origins to access the API
]


# Create the FastAPI app
app = FastAPI(title="Hydroponics Monitor System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow all origins (or specify a list of allowed origins)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Create the database directory if it doesn't exist
if not os.path.exists('database'):
    os.makedirs('database')

# Create static directory if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# Initialize static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Connect to SQLite database
def get_db_connection():
    conn = sqlite3.connect('database/hydroponics.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create the database and table if they don't exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        water_level REAL NOT NULL,
        ph_level REAL NOT NULL,
        temperature REAL NOT NULL,
        humidity REAL NOT NULL,
        tds_level REAL NOT NULL,
        dissolved_oxygen REAL NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

# Call the function to initialize the database
init_db()

# Define data models
class SensorReading(BaseModel):
    water_level: float
    ph_level: float
    temperature: float
    humidity: float
    tds_level: float
    dissolved_oxygen: float


# GET route for the main page
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# GET route for current sensor data
@app.get("/api/sensors/current", response_model=SensorReading)
async def get_latest_sensor_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM sensor_readings
    ORDER BY timestamp DESC
    LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No sensor data found")

    return {
        "timestamp": row["timestamp"],
        "water_level": row["water_level"],
        "ph_level": row["ph_level"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "tds_level": row["tds_level"],
        "dissolved_oxygen": row["dissolved_oxygen"]
    }

# GET route for historical sensor data
@app.get("/api/sensors/history")
async def get_sensor_history(hours: int = 24):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM sensor_readings
    WHERE timestamp >= datetime('now', ?)
    ORDER BY timestamp ASC
    ''', (f'-{hours} hours',))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert rows to a list of dictionaries
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "water_level": row["water_level"],
            "ph_level": row["ph_level"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "tds_level": row["tds_level"],
            "dissolved_oxygen": row["dissolved_oxygen"]
        })
    
    return history

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # Add these imports at the top
from datetime import datetime, timedelta

# Add this new data model class
class ManualSensorReading(BaseModel):
    timestamp: str  # ISO format timestamp
    water_level: float
    ph_level: float
    temperature: float
    humidity: float
    tds_level: float
    dissolved_oxygen: float

# Add a new POST route to manually add sensor data
@app.post("/api/sensors/manual")
async def add_manual_sensor_data(reading: ManualSensorReading):
    try:
        # Validate timestamp format
        timestamp = datetime.fromisoformat(reading.timestamp)
        
        # Save the data to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO sensor_readings 
        (timestamp, water_level, ph_level, temperature, humidity, tds_level, dissolved_oxygen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            reading.timestamp,
            reading.water_level,
            reading.ph_level,
            reading.temperature,
            reading.humidity,
            reading.tds_level,
            reading.dissolved_oxygen
        ))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Data added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding data: {str(e)}")


# Add batch simulation endpoint
@app.post("/api/sensors/simulate-batch")
async def simulate_batch_data(count: int = 100, interval_minutes: int = 15):
    try:
        current_time = datetime.now()
        readings = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for i in range(count):
            timestamp = current_time - timedelta(minutes=interval_minutes * i)
            data = generate_sensor_data()  # Use your existing function
            
            cursor.execute('''
            INSERT INTO sensor_readings 
            (timestamp, water_level, ph_level, temperature, humidity, tds_level, dissolved_oxygen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                data["water_level"],
                data["ph_level"],
                data["temperature"],
                data["humidity"],
                data["tds_level"],
                data["dissolved_oxygen"]
            ))
            
            readings.append({
                "timestamp": timestamp.isoformat(),
                **data
            })
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": f"Generated {count} readings", "samples": readings[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating data: {str(e)}")

# Add custom range endpoint
@app.get("/api/sensors/custom-range")
async def get_sensor_custom_range(start: str, end: str):
    try:
        # Validate date formats
        start_date = datetime.fromisoformat(start)
        end_date = datetime.fromisoformat(end)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM sensor_readings
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        ''', (start, end))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to a list of dictionaries
        history = []
        for row in rows:
            history.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "water_level": row["water_level"],
                "ph_level": row["ph_level"],
                "temperature": row["temperature"],
                "humidity": row["humidity"],
                "tds_level": row["tds_level"],
                "dissolved_oxygen": row["dissolved_oxygen"]
            })
        
        return history
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


