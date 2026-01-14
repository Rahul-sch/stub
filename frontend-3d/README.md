# Rig Alpha 3D Digital Twin

High-fidelity React Three Fiber visualization for industrial sensor pipeline.

## Installation

### Backend Dependencies (Flask-SocketIO)

```bash
cd c:\Users\rahul\Desktop\stubby\stub

# Install only the new packages (psycopg2-binary is already installed)
pip install flask-socketio==5.3.6 python-socketio==5.10.0 python-engineio==4.8.0
```

### Frontend Dependencies

```bash
cd c:\Users\rahul\Desktop\stubby\stub\frontend-3d

# Install with legacy peer deps to avoid version conflicts
npm install --legacy-peer-deps
```

## Running the Application

### 1. Start Backend (Terminal 1)
```bash
cd c:\Users\rahul\Desktop\stubby\stub
python dashboard.py
```

Expected output: `Starting Flask with SocketIO (WebSocket enabled for 3D Twin)`

### 2. Start Frontend (Terminal 2)
```bash
cd c:\Users\rahul\Desktop\stubby\stub\frontend-3d
npm run dev
```

### 3. Open Browser
Navigate to: http://localhost:3000

Click to enter the 3D world, then use:
- **WASD** - Move
- **Mouse** - Look around
- **Space** - Jump
- **Shift** - Sprint
- **ESC** - Release cursor

## Troubleshooting

### "Flask-SocketIO not available"
```bash
pip install flask-socketio==5.3.6 python-socketio==5.10.0 python-engineio==4.8.0
```

### "vite not found"
```bash
npm install --legacy-peer-deps
```

### Connection errors
1. Ensure Flask is running on port 5000
2. Check that Kafka producer is generating data
3. Verify database connection in Flask logs

## Architecture

```
Kafka → Consumer → PostgreSQL
                      ↓
                  Flask Dashboard (Port 5000)
                      ↓
              WebSocket (SocketIO @ 10Hz)
                      ↓
            React Frontend (Port 3000)
                      ↓
              React Three Fiber Canvas
                      ↓
         3D Rigs with Real-Time Animations
```
