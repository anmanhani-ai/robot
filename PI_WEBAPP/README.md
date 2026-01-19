# AgriBot Web Dashboard

Web-based control dashboard สำหรับหุ่นยนต์กำจัดวัชพืช

## 📁 Project Structure

```
PI_WEBAPP/
├── backend/                 # Python FastAPI
│   ├── main.py             # API Server
│   ├── data/               # JSON data files
│   │   ├── report.json     # Activity logs
│   │   └── status.json     # Robot status
│   └── requirements.txt
│
└── frontend/               # React + Vite
    ├── src/
    │   ├── components/     # React components
    │   ├── services/       # API service
    │   ├── App.jsx         # Main app
    │   └── index.css       # Tailwind styles
    ├── package.json
    └── tailwind.config.js
```

## 🚀 Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
# Server runs on http://localhost:8000
```

### Frontend (Development)
```bash
cd frontend
npm install
npm run dev
# App runs on http://localhost:5173
```

### Production Build
```bash
cd frontend
npm run build
# Static files in dist/ folder
# Backend serves these automatically
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Robot status (polling) |
| `/api/command` | POST | Send command (start/stop/reset) |
| `/api/logs` | GET | Activity logs |
| `/api/download` | GET | Download CSV report |
| `/api/reset` | POST | Clear report data |

## 🎮 Features

- **Real-time Status**: Weed count, distance, battery
- **Live Camera**: MJPEG stream (when connected)
- **Control Panel**: Start, Stop, Download, Reset
- **Activity Log**: Real-time event viewer
- **Mock Simulator**: Test without hardware

## 📱 Raspberry Pi Setup

1. Enable WiFi Hotspot on Pi
2. Run backend server
3. Connect phone/tablet to Pi WiFi
4. Open browser: `http://192.168.4.1:8000`
