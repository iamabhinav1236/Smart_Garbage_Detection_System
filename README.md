# Smart Garbage Detection System
### AI-Powered Real-Time Smart Dustbin Monitoring & Surveillance System

A production-grade, full-stack Edge AI web application designed for campus and smart city waste surveillance. It continuously ingests video streams from repurposed smartphone IP webcams, processes video frames in real time using **YOLOv8** and OpenCV, calculates dustbin interior fill percentages (%) using **Dual Region-of-Interest (ROI)** geometry, tracks floor overflow/litter, and automatically dispatches rich HTML email alerts with annotated snapshot evidence to caretakers upon crossing the **85% capacity threshold**.

---

## 🌟 Key Architectural Features

1. **Repurposed Edge Device as IP Camera**:
   - Zero dedicated sensor hardware cost. Repurposes standard Android/iOS smartphones running IP Webcam over local Wi-Fi (HTTP / RTSP).
2. **Dual-ROI Vision Pipeline**:
   - **Bin Interior ROI**: Isolates dustbin geometry to calculate true volumetric surface coverage and fill height.
   - **Floor Zone ROI**: Concurrently monitors the floor area outside the dustbin to detect litter spills and overflowing debris.
3. **Continuous AI Detection Engine**:
   - High-throughput **YOLOv8** object detection powered by ONNXRuntime / OpenCV DNN on CPU.
   - Real-time on-screen **Cyber HUD Overlay** displaying Bin ID, live fill percentage, status, and bounding boxes.
4. **State-Based 85% Alert & Cooldown Engine**:
   - Immediate SMTP alert with embedded snapshot proof on `NORMAL -> CRITICAL` transition.
   - Configurable cooldown window (default: 15 minutes) prevents caretaker inbox flooding.
   - Automatic hysteresis reset when the dustbin is emptied.
5. **Interactive Dual-ROI Calibration Tool**:
   - Web-based HTML5 canvas calibration tool + standalone OpenCV desktop utility (`scripts/calibrate_roi_standalone.py`).
6. **Multi-Bin Live Dashboard**:
   - Dynamic cards generated from SQLite/PostgreSQL-ready SQLAlchemy ORM.
   - Real-time WebSocket telemetry updates every second.
   - Demo mode with realistic synthetic dustbin simulation and manual capacity slider.

---

## 🏗️ Technology Stack

| Component | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, JavaScript (ES6+), React Router v7, Axios, Lucide Icons, Recharts |
| **Backend** | Python 3.12+, FastAPI, Uvicorn, WebSockets, Pydantic v2 |
| **Computer Vision** | YOLOv8 (ONNXRuntime / Ultralytics), OpenCV (`cv2`), NumPy, Pillow |
| **Database** | SQLite (Default local setup) / PostgreSQL via SQLAlchemy ORM |
| **Alerting** | Python `smtplib` / `email`, TLS/SSL, Gmail App Password support |

---

## 📁 Project Structure

```text
smart-garbage-system/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── detector.py          # YOLOv8 ONNX / OpenCV DNN inference wrapper
│   │   │   ├── fill_level.py        # Surface coverage & height fill estimation
│   │   │   ├── roi_manager.py       # Dual-ROI polygon coordinate math & HUD drawing
│   │   │   └── litter_detector.py   # Floor overflow & litter detection
│   │   ├── camera/
│   │   │   ├── camera_manager.py    # Multi-camera registry & lifecycle manager
│   │   │   ├── stream_worker.py     # Resilient frame capture & AI loop
│   │   │   └── mock_stream.py       # Realistic synthetic demo video generator
│   │   ├── email/
│   │   │   ├── email_service.py     # HTML email builder & SMTP sender
│   │   │   └── alert_manager.py     # Cooldown control & snapshot persistence
│   │   ├── models/                  # SQLAlchemy ORM models (User, Dustbin, Alert, etc.)
│   │   ├── routers/                 # FastAPI REST API & WebSocket endpoints
│   │   ├── schemas/                 # Pydantic request/response validation schemas
│   │   ├── utils/                   # Security (bcrypt, JWT), seeding, and logging
│   │   ├── config.py                # Pydantic Settings
│   │   ├── database.py              # Database engine & session maker
│   │   └── main.py                  # FastAPI application entrypoint
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/              # Navbar, Sidebar, BinCard, MetricCard, RoiModal
│   │   ├── context/                 # AuthContext & NotificationContext
│   │   ├── pages/                   # Welcome, Login, Dashboard, Details, Analytics, etc.
│   │   ├── services/                # Axios API client & WebSocket client
│   │   ├── styles/                  # Modular CSS architecture
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── models/
│   ├── yolov8n.onnx                 # Preloaded high-speed YOLOv8 weights
│   └── yolov8n.pt                   # PyTorch fallback weights
├── data/
│   ├── snapshots/                   # Annotated alert camera captures
│   └── logs/                        # System runtime logs
├── scripts/
│   ├── calibrate_roi_standalone.py  # Standalone OpenCV calibration GUI
│   ├── test_mock_stream.py          # AI pipeline test script
│   ├── run_backend.bat              # One-click Windows backend launcher
│   └── run_frontend.bat             # One-click Windows frontend launcher
├── README.md
└── .gitignore
```

---

## ⚡ Quick Start (Windows Local Setup)

### Prerequisites
- **Python 3.11 or 3.12** installed and on `PATH`.
- **Node.js 18+** and **npm** installed.
- VS Code or your preferred terminal.

### 1. Setup Backend
Open PowerShell / Command Prompt in the project folder:
```powershell
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Setup Frontend
In another terminal window:
```powershell
cd frontend
npm install
```

### 3. Start Both Services

#### Option A: One-Click Batch Launchers
Double click or run:
```powershell
# Terminal 1: Starts FastAPI on http://localhost:8000
.\scripts\run_backend.bat

# Terminal 2: Starts Vite Frontend on http://localhost:5173
.\scripts\run_frontend.bat
```

#### Option B: Manual Command Line
```powershell
# Terminal 1 (Backend)
.\venv\Scripts\activate
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# Terminal 2 (Frontend)
cd frontend
npm run dev
```

Visit **http://localhost:5173** in your web browser.

---

## 🔑 Default Administrator Credentials

| Username | Password | Access Level |
| :--- | :--- | :--- |
| `admin` | `admin123` | Full Administrator (Configured via seed data) |

---

## 📱 How to Use an Android Smartphone as an IP Webcam

1. Connect your Android smartphone to the **same Wi-Fi network** as your PC.
2. Install the free **IP Webcam** app from the Google Play Store (by Pavel Khlebovich).
3. Scroll down in the app and tap **Start Server**.
4. The phone displays an IP address, e.g.:
   ```text
   http://192.168.1.105:8080
   ```
5. In the Smart Garbage System:
   - Navigate to **Add Bin** or **Edit Bin**.
   - Set **IP Webcam URL** to:
     ```text
     http://192.168.1.105:8080/video
     ```
   - Click **TEST CAMERA** to verify connectivity.
   - Save the bin. The backend immediately streams and runs AI inference on your phone's feed!

---

## 📧 Gmail App Password Setup (for Real Email Alerts)

To enable automatic alerts sent to caretaker inboxes:
1. Go to your **Google Account** &rarr; **Security**.
2. Ensure **2-Step Verification** is turned ON.
3. Under 2-Step Verification, search for **App passwords**.
4. Create an App password named `SmartGarbageSystem`.
5. Copy the 16-character generated password (e.g., `abcd efgh ijkl mnop`).
6. In the Web Dashboard:
   - Go to **Caretaker / Email** page.
   - Enter your Gmail as **SMTP Username**.
   - Paste the 16-character code as **SMTP App Password**.
   - Set **SMTP Host**: `smtp.gmail.com`, **SMTP Port**: `587`.
   - Click **SAVE SETTINGS**.
   - Click **SEND TEST EMAIL** to test your setup.

---

## 🎯 Testing & Verification Checklist

1. **Demo Mode Live Stream**:
   - The default sample bins use built-in synthetic camera feeds with simulated waste accumulation.
   - Use the **Demo Capacity Slider** on any bin card to slide the fill level to 90%.
   - Notice the status badge immediately turns **CRITICAL** (pulsing red) and dispatches an alert!
2. **Interactive ROI Calibration**:
   - Click **CALIBRATE** on any bin card or the details page.
   - Click to mark the **Bin Interior ROI** (Cyan) and **Floor Zone ROI** (Amber).
   - Click **Save Calibration** to instantly update detection boundaries.
3. **Real-time WebSockets**:
   - Open the dashboard in two tabs: changes and telemetry sync live without refreshing!
4. **Historical Analytics**:
   - Visit the **Analytics** page to inspect line charts, status distribution pie charts, and alert frequency graphs.

---

## 🎓 Academic Presentation Credits

- **Institution**: GL Bajaj Institute of Technology & Management
- **Department**: Department of Computer Science & Engineering (AIML)
- **Session**: 2025-2026
- **Project Supervisor**: Dr. Santosh Srivastava
- **Project Team**:
  - Abhinav Srivastava (2501921530013)
  - Abhinav Singh (2501921530012)
  - Abhishek Maurya (2501921530018)
  - Abhishek Kumar Gupta (2501921530016)

---
Licensed under MIT. Production-ready for campus waste management and academic demonstration.
