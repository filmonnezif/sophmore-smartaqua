from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import random
import datetime
import uvicorn
import os
import cv2
from typing import List
from datetime import datetime, timedelta
import asyncio
from fastapi import WebSocket, WebSocketDisconnect


def generate_sensor_data():
    """Generate random sensor readings for testing"""
    return {
        "water_level": round(random.uniform(40, 95), 1),
        "ph_level": round(random.uniform(5.5, 8.5), 1),
        "temperature": round(random.uniform(18, 28), 1),
        "humidity": round(random.uniform(50, 85), 1),
        "tds_level": round(random.uniform(600, 1500), 0),
        "dissolved_oxygen": round(random.uniform(5, 8), 1)
    }

# Create the FastAPI app
app = FastAPI(title="Hydroponics Monitor System")

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
def ensure_no_camera_image():
    """Create a placeholder image for when the camera is not available"""
    no_camera_path = 'static/no_camera.jpg'
    if not os.path.exists(no_camera_path):
        try:
            # Create a black image with text
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, "No Camera Available", (120, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.imwrite(no_camera_path, img)
            print("Created placeholder camera image")
        except Exception as e:
            print(f"Error creating placeholder image: {e}")


def get_camera():
    """
    Try camera indexes 0 then 1.  If neither opens, return None.
    """
    for idx in (0, 1):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            return cap
        cap.release()
    return None

def generate_frames():
    """
    Generate MJPEG frames from the camera, or
    fall back to a placeholder if no camera is available.
    """
    camera = get_camera()
    if camera is None:
        ensure_no_camera_image()
        placeholder = open('static/no_camera.jpg', 'rb').read()
        while True:
            yield (
              b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' +
              placeholder +
              b'\r\n'
            )
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (255, 255, 255), 2)
            ret, buf = cv2.imencode('.jpg', frame)
            yield (
              b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' +
              buf.tobytes() +
              b'\r\n'
            )
    finally:
        camera.release()

@app.get("/api/webcam/stream")
async def video_stream():
    """Endpoint that returns a streaming response of webcam frames"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )    
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
        # no real data → return a generated “fallback” reading
        data = generate_sensor_data()
        return {
            "water_level": data["water_level"],
            "ph_level": data["ph_level"],
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "tds_level": data["tds_level"],
            "dissolved_oxygen": data["dissolved_oxygen"],
            # timestamp of this fallback
            "timestamp": datetime.now().isoformat()
        }

    return {
        "water_level": row["water_level"],
        "ph_level": row["ph_level"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "tds_level": row["tds_level"],
        "dissolved_oxygen": row["dissolved_oxygen"],
        "timestamp": row["timestamp"]
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

@app.websocket("/ws/webcam")
async def websocket_webcam(websocket: WebSocket):
    print("🟢 [WS] client connecting…")
    await websocket.accept()
    camera = get_camera()
    if not camera:
        print("⚠️ [WS] no camera, streaming placeholder")
        ensure_no_camera_image()
        placeholder = open('static/no_camera.jpg', 'rb').read()
        try:
            while True:
                await websocket.send_bytes(placeholder)
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            print("🔴 [WS] placeholder client disconnected")
        return

    try:
        print("🟢 [WS] streaming actual camera frames")
        while True:
            ok, frame = camera.read()
            if not ok:
                break
            # draw timestamp…
            ret, buf = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            await websocket.send_bytes(buf.tobytes())
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        print("🔴 [WS] client disconnected")
    finally:
        camera.release()
        print("🔴 [WS] camera released")

# Run the server
if __name__ == "__main__":
    ensure_no_camera_image()
    uvicorn.run(app, host="0.0.0.0", port=8000)
