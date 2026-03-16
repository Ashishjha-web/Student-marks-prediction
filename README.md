# 🎓 VisionED – AI-Powered Student Performance Predictor

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Random%20Forest-green)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-ML%20Library-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

VisionED is an **AI-powered Student Performance Prediction System** that uses **Machine Learning (Random Forest Regressor)** integrated into a **Flask-based web application**.

The system predicts **End-Semester Marks and Attendance** based on students' academic performance indicators such as previous marks and attendance.

This project was developed as a **Minor Project** for
**New Government Polytechnic, Patna-13 (NGP)**.

VisionED provides a structured academic platform where students and administrators can manage **academic analytics, study materials, announcements, and academic queries**.

---

# 🚀 Core Features

* AI-based prediction of End-Semester Marks and Attendance
* Branch & Semester specific academic analysis
* Profile completion-based secure dashboard access
* Structured CSV-based academic data upload system
* Study material upload and management by Admin
* Announcement management system
* Academic query submission and Admin response system
* Role-based access control (Student / Admin / Super Admin)
* Student performance analytics dashboard

---

# 🖼️ Application Screenshots

## 🏠 Home Page

Landing page with role-based login and signup system.

![Home Page](https://github.com/user-attachments/assets/7b978ae6-47e2-47e2-88cd-7ee0cb9aeb0a)

---

## 🎓 Student Dashboard

Students can access prediction analysis, study materials, announcements, and academic queries.

![Student Dashboard](https://github.com/user-attachments/assets/66e50bfd-ace5-4bf7-9768-f994de18d9eb)

---

## 👨‍🏫 Admin Dashboard

Administrative control panel used to manage users, upload academic data, and train prediction models.

![Admin Dashboard](https://github.com/user-attachments/assets/30b4d22d-023b-4db6-b105-40ad22b07de9)

---

## 📂 Analytics Data Uploader

Admin selects **Branch and Semester**, downloads the structured template, fills previous batch data (marks & attendance), and uploads it to train the model.

![Analytics Uploader](https://github.com/user-attachments/assets/656003a4-3915-4a32-ab34-de07cadf517b)

---

## 📊 Performance Analytics – Part 1

Subject-wise prediction results generated using the **Random Forest Regressor** model.

![Performance Analysis 1](https://github.com/user-attachments/assets/9fe392da-4d74-4585-a3f5-3625c9a31302)

---

## 📊 Performance Analytics – Part 2

Detailed analytics insights based on student academic inputs.

![Performance Analysis 2](https://github.com/user-attachments/assets/8a65b4ab-f507-4e76-bd76-2d56d18f750e)

---

## 👥 Registered Users Management

Admin interface used to manage students and other administrators.

![Registered Users](https://github.com/user-attachments/assets/5d2983e1-2b60-4f4a-b52c-4547c79ff876)

---

# 🛠️ Tech Stack

## Backend

* Python
* Flask
* Flask-SQLAlchemy
* Werkzeug

## Machine Learning

* Scikit-learn (Random Forest Regressor)
* Pandas
* NumPy
* OpenPyXL

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript

## Database

* SQLite

---

# 🤖 Machine Learning Approach

The system uses **Scikit-learn’s Random Forest Regressor** to model nonlinear relationships between academic indicators and final end-semester outcomes.

### 📥 Input Features

* Previous Semester Marks
* Previous Semester Attendance Percentage
* Internal Subject Marks (entered by students during prediction)

### 🎯 Target Variables

* Final End-Semester Marks
* Final End-Semester Attendance

The model is trained **separately for each Branch and Semester** using structured historical academic data from previous student batches.

Once trained, the system predicts **expected end-semester marks and attendance** based on student academic inputs.

---

# 📂 Project Structure

```text id="struct01"
VisionED-performance-predictor/
│
├── static/
│   └── uploads/
│       └── images/
│           ├── admin_default.png
│           ├── student_default.png
│           └── profile images...
│
├── templates/
│   ├── admin_dashboard.html
│   ├── admin_material_uploader.html
│   ├── admin_announcements.html
│   ├── registered_users.html
│   ├── student_dashboard.html
│   ├── student_analytics.html
│   ├── profile_student.html
│   ├── profile_admin.html
│   ├── login.html
│   ├── signup.html
│   ├── index.html
│   ├── contact.html
│   ├── blog.html
│   ├── faq.html
│   ├── privacy.html
│   ├── team.html
│   └── other templates...
│
├── app.py
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation & Setup

## 1️⃣ Clone the Repository

```bash id="clone01"
git clone https://github.com/sagarcs818/VisionED-performance-predictor.git
cd VisionED-performance-predictor
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash id="venvwin"
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash id="venvunix"
python3 -m venv venv
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash id="install01"
pip install -r requirements.txt
```

---

## 4️⃣ Configure Secret Key

Open `app.py` and update:

```python id="secret01"
app.secret_key = "your_strong_secret_key_here"
```

🔐 This key is used to:

* Secure login sessions
* Protect admin authentication
* Prevent session tampering
* Enable flash messages

Replace it with a strong random string.

⚠ If this key changes later, all users will be logged out automatically.

---

## 5️⃣ Default Admin Codes (First Run)

* Admin Signup Code: `1234`
* Super Admin Code: `5678`

These can be changed later from the **Admin Profile Page**.

---

## 6️⃣ Run the Application

```bash id="run01"
python app.py
```

---

## 7️⃣ Open in Browser

```
http://127.0.0.1:5000/
```

---

# 🔄 System Workflow

The following diagram illustrates how users navigate through the system and how workflows are connected:

![Workflow diagram](https://github.com/user-attachments/assets/23a00a5b-0e33-47ed-9945-04fdd4c3ac4a)

---

# 👨‍💼 Administrator Workflow

## 🔐 Step 1: Registration & Access

1. Register using the provided Admin Code
2. Login to the system
3. Complete required profile details
4. Access the Admin Dashboard

⚠ **Profile completion is required to access dashboard features.**

---

## 📊 Step 2: Upload Historical Academic Data

1. From the Admin Dashboard, navigate to **Material Uploader**
2. Select **Upload Analytics Data**
3. Choose:
   * Branch
   * Semester
4. Download the structured CSV template generated by the system

The template includes required columns such as:

* Previous Semester Marks
* Attendance Percentage
* Final End-Semester Marks

---

## 📂 Step 3: Train the Prediction Model

1. Fill the CSV template with historical student data
2. Ensure the column structure is correct
3. Upload the completed CSV file
4. The system trains the Random Forest model

Once uploaded successfully, the system becomes ready to generate predictions for students.

---

## 📚 Administrator Dashboard Capabilities

After profile completion, Administrators can:

* 📂 Upload study materials
* 📢 Post announcements
* ❓ Respond to student queries
* 👥 Manage registered users
* 📊 View student prediction analytics
* 🛡 Super Admin privileges for managing other admins

---

# 👨‍🎓 Student Workflow

## 🔐 Step 1: Registration & Access

1. Register as a Student
2. Login to the system
3. Complete academic profile:
   * Branch
   * Semester

⚠ **Profile completion is required to access dashboard features.**

---

## 📈 Step 2: Performance Analysis

Navigate to **Performance Analysis** and enter:

* Internal Subject Marks
* Previous Semester Marks
* Previous Semester Attendance Percentage

---

## 🤖 Step 3: AI-Based Prediction

1. Submit academic inputs
2. The system runs the trained Random Forest model
3. Predicted End-Semester Marks and Attendance are displayed

---

## 📚 Student Dashboard Features

After profile completion, Students can:

* 📊 Perform performance analysis
* 📂 View & download study materials
* 📢 View announcements
* ❓ Submit academic queries
* 👍 Interact with posts (Like / Reply)

---

# 🎯 Project Objective

VisionED aims to:

* Identify students at academic risk early
* Provide AI-based academic insights
* Improve academic decision making
* Digitize academic analytics in institutions

---

⭐ If you found this project useful, consider **starring the repository**.

---

# 📜 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for more information.
