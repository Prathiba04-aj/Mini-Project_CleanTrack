# Clean Track: AI-Based Smart Waste Segregation 🌍

**Clean Track** is a full-stack web application designed to modernize waste management using Artificial Intelligence. It helps residents correctly segregate waste and allows local municipalities to manage community waste reports in real-time.

---

## 🚀 Features

### For Residents
- **AI Material Classifier**: Upload an image to identify waste types (Plastic, Paper, Metal, etc.) and receive instant disposal steps.
* **Live Camera Scanner**: Real-time waste detection using your device's camera.
* **Smart Reporting**: Report local waste accumulation with automatic GPS location fetching and photo uploads.
* **Community Dashboard**: Track the status of your reports and see community-wide impact.

### For Municipal Staff
* **Review Portal**: High-level overview of all community reports.
* **Moderation Tools**: Verify valid reports, mark fake entries, and resolve issues once cleaned.
* **Analytics**: Real-time stats on total, verified, and pending reports.

---

## 🛠️ Technology Stack
- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **AI/ML**: TensorFlow / Keras (CNN Model)
- **Frontend**: Clean CSS3, HTML5, Vanilla JavaScript
- **Animations**: CSS Keyframes & Micro-interactions
- **APIs**: OpenStreetMap (Nominatim) for Reverse Geocoding

---

## 📦 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/Mini-Project_CleaTrack.git
   cd Mini-Project_CleaTrack
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the App:** 
   Open `http://127.0.0.1:5000` in your browser.

---

## 👤 Admin Access (Demo)
For demonstration purposes, a default admin account is automatically created on first run:
- **Username**: `admin`
- **Password**: `admin123`

---

## 🍃 Sustainability Impact
Clean Track aims to reduce landfill contamination by educating users on recyclability at the source. By bridging the gap between residents and municipal staff, we ensure a faster, smarter, and cleaner urban environment.
