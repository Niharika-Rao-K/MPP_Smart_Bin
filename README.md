# ♻️ Smart Recycling System (MPP Monorepo)

An automated waste classification, weight verification, and reward processing platform featuring a React admin analytics dashboard, an edge microcontroller node, and a semantic RAG engine.

---

## 📁 Repository Structure

```text
MPP/
├── mpp-admin-dashboard/    # React.js Operations & Analytics Dashboard
├── mpp-semantic-rag/       # FastAPI + ChromaDB Semantic Verification Engine
├── .gitignore              # Monorepo git exclusion rules
└── README.md               # Project documentation & setup guide
🛠️ Tech Stack & Requirements
Frontend: React.js, Tailwind CSS, Recharts (Node.js v18+)

Backend: Python 3.10+, FastAPI, ChromaDB, Uvicorn

Firmware: ESP32-CAM, HX711 Load Cell, MG90S Pan-Tilt Servos (Arduino IDE / C++)

🚀 Getting Started
1. Clone the Repository
Bash
git clone [https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git)
cd YOUR_REPO_NAME
💻 2. Admin Dashboard Setup (mpp-admin-dashboard)
Open a terminal in the root directory:

Bash
# Navigate to the dashboard directory
cd mpp-admin-dashboard

# Install React dependencies
npm install

# Start the local development server
npm start
The Dashboard UI will open at http://localhost:3000

⚙️ 3. Semantic RAG Engine Setup (mpp-semantic-rag)
Open a second terminal window in the root directory:

Bash
# Navigate to the backend directory
cd mpp-semantic-rag

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (Command Prompt / PowerShell):
.\venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt

# Start the FastAPI engine
uvicorn main:app --reload
The backend API will run at http://localhost:8000 (Swagger docs available at http://localhost:8000/docs)

🔄 Team Git Workflow Rules
To prevent overwriting code or causing merge conflicts on main:

Pull the latest changes before starting work:

Bash
git pull origin main
Create a dedicated branch for your task:

Bash
git checkout -b feature/your-feature-name
Commit and push your work:

Bash
git add .
git commit -m "Add: description of updates made"
git push origin feature/your-feature-name
Create a Pull Request (PR) on GitHub to merge your feature branch into main.
