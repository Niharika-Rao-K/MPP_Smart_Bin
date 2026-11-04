# Recycle2Earn – IoT-Based Smart Waste Segregation and Reward System

An IoT-enabled smart waste management system that combines computer vision, semantic material verification, load-cell sensing, automated waste segregation and blockchain-based rewards to encourage responsible recycling.

## 1. Project Overview

Recycle2Earn is an intelligent waste collection and segregation system designed to automate waste identification, verify deposited material and reward users for valid recycling contributions.

Users access the web application by scanning a QR code attached to the smart bin. The application captures an image of the waste using an ESP32-CAM and sends it to the backend for classification. A MobileNetV3-Small deep learning model identifies the waste category, while a semantic material retrieval and weight-validation system verifies whether the deposited item matches its expected material profile.

For accepted deposits, the system calculates the corresponding reward, records the deposit and integrates with an Ethereum Sepolia ERC-20 token contract. The ESP32-based hardware then controls the segregation mechanism to direct the waste into the appropriate collection compartment.

The system integrates:

- IoT-based sensing and automated segregation.
- Deep learning-based waste classification.
- Semantic material retrieval and weight verification.
- Progressive Web Application (PWA).
- FastAPI backend and PostgreSQL database.
- Ethereum-based ERC-20 reward integration.

## 2. Key Features

### Intelligent Waste Classification
- Uses a MobileNetV3-Small image classification model.
- Supports nine trained waste categories.
- Uses a confidence threshold to determine whether a classification is sufficiently reliable.

### Semantic Material Retrieval and Weight Verification
- Retrieves relevant material profiles from a ChromaDB vector database.
- Uses material information stored in `waste_knowledge.json`.
- Compares measured weight against the expected material-specific weight range.
- Helps identify invalid, inconsistent or potentially contaminated deposits.

### IoT-Based Weight Measurement
- Uses an ESP32-WROOM development board.
- Uses an HX711 load-cell amplifier for weight measurement.
- Communicates sensor readings to the backend through an API-based request workflow.

### Automated Waste Segregation
- Uses servo motors to direct accepted waste into the appropriate compartment.
- Supports metal, e-waste, plastic and rejection routing.

### Progressive Web Application
- Provides a mobile-friendly interface accessible through a QR code.
- Supports installation as a Progressive Web Application.
- Integrates user authentication and the waste deposit workflow.

### Blockchain-Based Rewards
- Integrates an ERC-20 reward token deployed on Ethereum Sepolia.
- Uses Web3 integration for blockchain interactions.
- Connects validated recycling deposits with token reward processing.

### Backend and Database
- FastAPI provides REST API endpoints.
- PostgreSQL stores application data.
- ChromaDB supports semantic material retrieval.

## 3. System Architecture

The project consists of three primary components:

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React, JavaScript, HTML, CSS | User authentication and deposit interface |
| Backend | Python, FastAPI | Classification, validation, rewards and APIs |
| Hardware | ESP32, ESP32-CAM, HX711, servo motors | Image capture, weight measurement and segregation |
| Database | PostgreSQL | Persistent application data |
| Vector Database | ChromaDB | Semantic material profile retrieval |
| Blockchain | Solidity, Ethereum Sepolia, ERC-20 | Token reward integration |

### High-Level Workflow

1. The user scans the QR code attached to the smart bin.
2. The QR code opens the web application.
3. The user authenticates and initiates a waste deposit.
4. The ESP32-CAM captures an image of the waste.
5. The backend classifies the image using the trained MobileNetV3-Small model.
6. The semantic retrieval system obtains the relevant material profile.
7. The HX711 load-cell system measures the deposited item's weight.
8. The backend validates the measured weight against the expected material profile.
9. Invalid deposits are rejected.
10. Valid deposits proceed through reward calculation and deposit recording.
11. The blockchain integration processes the corresponding ERC-20 reward.
12. The ESP32 controls the segregation mechanism to route the accepted waste.

## 4. Machine Learning Model

The project uses a MobileNetV3-Small architecture for image classification.

**Supported waste categories:**

1. `coca_cola_can`
2. `dairy_milk_wrapper`
3. `diet_coke`
4. `general_metal`
5. `general_plastic`
6. `pepsi_can`
7. `ram_stick`
8. `red_bull_can`
9. `snickers_wrapper`

The trained model and its corresponding class labels are stored in:

```text
mpp-semantic-rag/
└── app/
    └── models/
        ├── best_nine_item_model.pth
        └── nine_item_classes.json
```

The classifier uses a confidence threshold of 0.75 in the image classification workflow.

## 5. Weight Verification and Material Validation

The semantic material verification system retrieves material profiles and validates the deposited item's measured weight.

The accepted weight condition is:

W(min) <= W(measured) <= W(max)


Where:

- W(measured): Measured weight reported by the load-cell system.
- W(min): Minimum acceptable weight for the material profile.
- W(max): Maximum acceptable weight for the material profile.

Material profiles are maintained in:

```text
mpp-semantic-rag/data/waste_knowledge.json
```

ChromaDB stores the corresponding semantic representations for retrieval.

The database can be initialized using the project's seeding utility.

## 6. Hardware Components

| Component | Purpose |
|---|---|
| ESP32-WROOM | Sensor communication and hardware control |
| AI Thinker ESP32-CAM | Waste image capture |
| HX711 | Load-cell signal amplification and conversion |
| Load Cell | Weight measurement |
| Servo Motors | Waste segregation mechanism |
| Smart Bin Compartments | Collection of segregated waste |

### ESP32 Pin Configuration

| Component | ESP32 GPIO |
|---|---|
| HX711 DT | GPIO 4 |
| HX711 SCK | GPIO 5 |
| Pan Servo | GPIO 18 |

Refer to the firmware directory for the hardware-specific implementation and configuration.

## 7. Repository Structure

```text
MPP_Smart_Bin/
│
├── firmware/
│   ├── esp32_camera_loadcell/
│   │   ├── CameraWebServer.ino
│   │   ├── app_httpd.cpp
│   │   ├── board_config.h
│   │   ├── camera_index.h
│   │   ├── camera_pins.h
│   │   └── partitions.csv
│   │
│   └── esp32_loadcell/
│       ├── esp32_loadcell.ino
│       └── secrets.example.h
│
├── mpp-admin-dashboard/
│   ├── public/
│   │   ├── dashboard.html
│   │   ├── index.html
│   │   ├── manifest.json
│   │   └── sw.js
│   │
│   └── src/
│       ├── components/
│       ├── App.js
│       ├── App.css
│       └── index.js
│
├── mpp-semantic-rag/
│   ├── app/
│   │   ├── abi/
│   │   ├── database/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   │
│   ├── data/
│   │   ├── waste_knowledge.json
│   │   └── rate_history.json
│   │
│   ├── tests/
│   └── test_waste_retrieval.py
│
├── .gitignore
├── README.md
└── requirements.txt
```

### Directory Description

- `firmware/`: ESP32-CAM and load-cell firmware.
- `mpp-admin-dashboard/`: React frontend and standalone PWA dashboard.
- `mpp-semantic-rag/app/routes/`: Authentication, bin, deposit, sensor, leaderboard and rate APIs.
- `mpp-semantic-rag/app/services/`: Classification, semantic retrieval, material validation, sensor fusion, weight processing and blockchain integration.
- `mpp-semantic-rag/app/database/`: Database connection and models.
- `mpp-semantic-rag/app/models/`: Trained classification model and class labels.
- `mpp-semantic-rag/app/abi/`: Blockchain contract ABI used by the backend.
- `mpp-semantic-rag/data/`: Material knowledge profiles and rate history.
- `mpp-semantic-rag/tests/`: Backend tests.

## 8. Software Requirements

- Python 3.10 or later (use a version compatible with the installed dependencies).
- Node.js and npm.
- Arduino IDE.
- Git.
- PostgreSQL.
- Ethereum-compatible wallet for blockchain testing.

## 9. Local Setup

### A. Clone the Repository

```bash
git clone https://github.com/Niharika-Rao-K/MPP_Smart_Bin.git
cd MPP_Smart_Bin
```

### B. Backend Setup

Create and activate a virtual environment:

**Windows PowerShell:**

```powershell
cd mpp-semantic-rag

python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install CPU-only PyTorch and Torchvision:

```powershell
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
```

Install the remaining dependencies from the root requirements file:

```powershell
pip install -r ..\requirements.txt
```

Configure the required environment variables, including database and blockchain settings, using your own credentials.

Initialize the material knowledge database:

```powershell
python -m app.utils.seed_db
```

Start the FastAPI backend:

```powershell
uvicorn app.main:app --reload
```

The local backend will normally be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### C. Frontend Setup

Open another terminal:

```powershell
cd mpp-admin-dashboard
npm install
```

Start the React development server:

```powershell
npm start
```

Create a production build:

```powershell
npm run build
```

The frontend API configuration must point to the appropriate backend URL.

The standalone PWA dashboard is maintained in the `public/` directory.

### D. Hardware Setup

1. Open the appropriate firmware project in Arduino IDE.
2. Select the correct ESP32 board.
3. Configure Wi-Fi credentials using the appropriate local secrets configuration.
4. Connect the ESP32-CAM and load-cell hardware according to the firmware pin configuration.
5. Upload the firmware to the corresponding ESP32 board.
6. Configure the backend URL and bin identification used by the firmware.

Do not commit personal Wi-Fi credentials, private keys or other secrets to GitHub.

## 10. Deployment

The project uses separate deployment platforms for its frontend and backend.

| Component | Deployment Platform |
|---|---|
| Frontend / PWA | Vercel |
| FastAPI Backend | Render |
| Relational Database | PostgreSQL |
| Blockchain | Ethereum Sepolia |

### Backend Deployment

The backend is deployed on Render.

Configure:

**Root Directory**

```text
mpp-semantic-rag
```

**Build Command**

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision && pip install -r ../requirements.txt
```

**Start Command**

```bash
python -m app.utils.seed_db && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Configure the required environment variables through Render's environment settings.

### Frontend Deployment

The React frontend and PWA are deployed separately using Vercel.

Configure the frontend's API base URL to point to the deployed FastAPI backend.

Ensure that the backend CORS configuration permits the deployed frontend origin.

## 11. Testing

The backend includes tests for material validation, rate tracking, rate APIs and other supporting functionality.

Run the test suite from the backend directory:

```powershell
cd mpp-semantic-rag
python -m pytest
```

Individual test scripts are also available for waste retrieval and weight comparison.

## 12. Security Considerations

- Never commit `.env` files or private credentials.
- Keep blockchain private keys outside the source code.
- Configure CORS for trusted frontend origins.
- Use secure database credentials.
- Keep Wi-Fi credentials out of public firmware files.
- Validate sensor readings and deposit requests on the backend.

**Recycle2Earn – Making Recycling Intelligent, Automated and Rewarding.**
