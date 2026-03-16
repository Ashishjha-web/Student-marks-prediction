from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import os
from functools import wraps
from datetime import datetime
import io
import re
import openpyxl
from sqlalchemy import inspect, text, desc, String, Integer
from sqlalchemy.sql.expression import cast
from sqlalchemy.orm import joinedload, subqueryload


app = Flask(__name__)
app.secret_key = "your_secret_key"

# --- MODIFICATION START: Updated folder configuration ---
UPLOAD_FOLDER = 'static/uploads'
PROFILE_IMG_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'pptx', 'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_IMG_FOLDER, exist_ok=True)
NOTES_FOLDER = os.path.join(UPLOAD_FOLDER, 'notes')
os.makedirs(NOTES_FOLDER, exist_ok=True)
ANNOUNCEMENTS_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'announcements')
os.makedirs(ANNOUNCEMENTS_FOLDER, exist_ok=True)
DATA_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'student_data')
os.makedirs(DATA_FOLDER, exist_ok=True)
# --- MODIFICATION END ---


# ================== DATABASE SETUP ==================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///visioned.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ================== MODELS ==================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_forum_blocked = db.Column(db.Boolean, default=False)
    blocked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    blocker = db.relationship('User', remote_side=[id])
    queries = db.relationship('Query', backref='author', lazy=True, cascade="all, delete-orphan")
    replies = db.relationship('Reply', backref='author', lazy=True, cascade="all, delete-orphan")
    hearts = db.relationship('Heart', back_populates='author', lazy=True, cascade="all, delete-orphan")
    student_info = db.relationship('StudentInfo', backref='user', uselist=False, cascade="all, delete-orphan")
    admin_info = db.relationship('AdminInfo', backref='user', uselist=False, cascade="all, delete-orphan")
    study_materials = db.relationship('StudyMaterial', back_populates='uploader_user', lazy=True, cascade="all, delete-orphan")
    announcements = db.relationship('Announcement', back_populates='user', lazy=True, cascade="all, delete-orphan")
    analytics_files = db.relationship('AnalyticsFile', back_populates='uploader_user', lazy=True, cascade="all, delete-orphan")

class StudentInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    name = db.Column(db.String(150))
    reg_no = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(150))
    branch = db.Column(db.String(50))
    sem = db.Column(db.Integer)
    phone = db.Column(db.String(20))
    # --- MODIFICATION START: Updated default path ---
    profile_photo = db.Column(db.String(200), default="images/student_default.png")
    # --- MODIFICATION END ---


class AdminInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(50))
    # --- MODIFICATION START: Updated default path ---
    profile_photo = db.Column(db.String(200), default="images/admin_default.png")
    # --- MODIFICATION END ---

class Config(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)

class StudentMarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject_id = db.Column(db.String(50), nullable=False)
    marks = db.Column(db.Float, nullable=False)

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    edited = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    replies = db.relationship('Reply', backref='query', lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('QueryVote', backref='voted_query', lazy=True, cascade="all, delete-orphan")
    hearts = db.relationship('Heart', backref='hearted_query', lazy=True, cascade="all, delete-orphan")

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    edited = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('reply.id'), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    children = db.relationship('Reply', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('ReplyVote', backref='reply', lazy=True, cascade="all, delete-orphan")
    hearts = db.relationship('Heart', backref='hearted_reply', lazy=True, cascade="all, delete-orphan")

class QueryVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)

class ReplyVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)

class Heart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=True)
    reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'), nullable=True)
    author = db.relationship('User', back_populates='hearts')

class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.String(50), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploader_user = db.relationship('User', back_populates='study_materials')

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    department = db.Column(db.String(50), nullable=False, default='ALL_BRANCHES')
    semester = db.Column(db.Integer, nullable=True)
    attached_files = db.Column(db.Text, nullable=True)
    edited = db.Column(db.Boolean, default=False) # Add this line
    user = db.relationship('User', back_populates='announcements')

class AnalyticsFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False, unique=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploader_user = db.relationship('User', back_populates='analytics_files')


with app.app_context():
    db.create_all()
    try:
        inspector = inspect(db.engine)
        
        table_name = 'announcement'
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        with db.engine.connect() as con:
            if 'department' not in columns:
                con.execute(text('ALTER TABLE announcement ADD COLUMN department VARCHAR(50) NOT NULL DEFAULT "ALL_BRANCHES"'))
            if 'semester' not in columns:
                con.execute(text('ALTER TABLE announcement ADD COLUMN semester INTEGER'))
            con.commit()

        table_name = 'query'
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        with db.engine.connect() as con:
            if 'is_locked' not in columns:
                con.execute(text('ALTER TABLE query ADD COLUMN is_locked BOOLEAN DEFAULT false'))
            if 'is_pinned' not in columns:
                con.execute(text('ALTER TABLE query ADD COLUMN is_pinned BOOLEAN DEFAULT false'))
            con.commit()

        table_name = 'reply'
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        with db.engine.connect() as con:
            if 'is_pinned' not in columns:
                con.execute(text('ALTER TABLE reply ADD COLUMN is_pinned BOOLEAN DEFAULT false'))
            con.commit()

        table_name = 'user'
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        with db.engine.connect() as con:
            if 'is_forum_blocked' not in columns:
                con.execute(text('ALTER TABLE user ADD COLUMN is_forum_blocked BOOLEAN DEFAULT false'))
            if 'blocked_by_id' not in columns:
                con.execute(text('ALTER TABLE user ADD COLUMN blocked_by_id INTEGER REFERENCES user(id)'))
            con.commit()

    except Exception as e:
        print(f"WARNING: Could not inspect or update database schema. {e}")
    
    if not Config.query.filter_by(key='admin_code').first():
        db.session.add(Config(key='admin_code', value='1234'))
        db.session.commit()
    if not Config.query.filter_by(key='super_admin_code').first():
        db.session.add(Config(key='super_admin_code', value='5678'))
        db.session.commit()
    if not Config.query.filter_by(key='is_chat_locked').first():
        db.session.add(Config(key='is_chat_locked', value='false'))
        db.session.commit()

# ================== DYNAMIC SUBJECT DATA & ML MODEL ==================
SUBJECTS = {
    'CSE': {
        1: [{'id': 'math1', 'name': 'MATHEMATICS-I'}, {'id': 'phy1', 'name': 'APPLIED PHYSICS-I'}, {'id': 'graphics', 'name': 'ENGG. GRAPHICS'}, {'id': 'chem', 'name': 'APPLIED CHEMISTRY'}, {'id': 'comm_skills', 'name': 'COMM. SKILLS IN ENGLISH'}],
        2: [{'id': 'math2', 'name': 'MATHEMATICS-II'}, {'id': 'phy2', 'name': 'APPLIED PHYSICS-II'}, {'id': 'mechanics', 'name': 'ENGG. MECHANICS'}, {'id': 'it_sys', 'name': 'INTRODUCTION TO IT SYSTEMS'}, {'id': 'eee', 'name': 'FUNDA OF ELECT AND EC ENGG'}],
        3: [{'id': 'discrete_math', 'name': 'DISCRETE MATHEMATICS'}, {'id': 'c_prog', 'name': "COMPUTER PROG THROUGH 'C'"}, {'id': 'digi_ec', 'name': 'DIGI EC AND MICROPRO'}, {'id': 'coa', 'name': 'COMPUTER ORG AND ARCH'}, {'id': 'web_tech', 'name': 'WEB TECHNOLOGY'}],
        4: [{'id': 'dbms', 'name': 'DATABASE MANAGEMENT SYSTEM'}, {'id': 'dsa', 'name': 'DATA STRUCTURE & ALGO. USING C'}, {'id': 'python', 'name': 'PYTHON PROGRAMMING'}, {'id': 'os', 'name': 'OPERATING SYSTEM'}, {'id': 'cg', 'name': 'COMPUTER GRAPHICS'}],
        5: [{'id': 'java', 'name': 'OOP through Java'}, {'id': 'iot', 'name': 'Internet of Things (Basics)'}, {'id': 'mc', 'name': 'Mobile Computing'}, {'id': 'mt', 'name': 'Multimedia Technology'}, {'id': 'chn', 'name': 'Computer Hardware & Networking'}],
        6: [{'id': 'data_sci', 'name': 'Data Sciences: Data Warehousing and Data Mining'}, {'id': 'cns', 'name': 'Computer Network Security'}, {'id': 'iot_adv', 'name': 'Internet of Things (Advance)'}, {'id': 'entrepreneurship', 'name': 'Entrepreneurship and start up'}, {'id': 'swe', 'name': 'Software Engineering'}]
    },
    'CE': {
        1: [{'id': 'math2', 'name': 'MATHEMATICS-II'}, {'id': 'phy2', 'name': 'APPLIED PHYSICS-II'}, {'id': 'mechanics', 'name': 'ENGG. MECHANICS'}, {'id': 'it_sys', 'name': 'INTRODUCTION TO IT SYSTEMS'}, {'id': 'eee', 'name': 'FUNDA OF ELECT AND EC ENGG'}],
        2: [{'id': 'math1', 'name': 'MATHEMATICS-I'}, {'id': 'phy1', 'name': 'APPLIED PHYSICS-I'}, {'id': 'graphics', 'name': 'ENGG. GRAPHICS'}, {'id': 'chem', 'name': 'APPLIED CHEMISTRY'}, {'id': 'comm_skills', 'name': 'COMM. SKILLS IN ENGLISH'}],
        3: [{'id': 'bcm', 'name': 'Building construction and constructing material'}, {'id': 'surveying', 'name': 'Basic surveying'}, {'id': 'mom', 'name': 'Mechanics of materials'}, {'id': 'concrete', 'name': 'Concrete technology'}, {'id': 'geo_tech', 'name': 'Geo technical engineering'}],
        4: [{'id': 'tos', 'name': 'Theory of structure'}, {'id': 'transport', 'name': 'Transportation engineering'}, {'id': 'bpd', 'name': 'Building planning and drawings'}, {'id': 'hydraulic', 'name': 'Hydraulic'}, {'id': 'adv_surveying', 'name': 'Advance surveying'}],
        5: [{'id': 'precast', 'name': 'Precast and prestressed concrete'}, {'id': 'iot', 'name': 'Iot(basic)'}, {'id': 'wre', 'name': 'Water resource engineering'}, {'id': 'steel_rcc', 'name': 'Steel and RCC'}, {'id': 'estimation', 'name': 'Estimation and costing'}],
        6: [{'id': 'entrepreneurship', 'name': 'ENTREPRENEURSHIP AND START-UPS'}, {'id': 'phe', 'name': 'PUBLIC HEALTH ENGINEERING'}, {'id': 'ads', 'name': 'ADVANCED DESIGN OF STRUCTURES'}, {'id': 'tendering', 'name': 'TENDERING AND ACCOUNTS'}, {'id': 'iot_adv', 'name': 'INTERNET OF THINGS (ADVANCE)'}]
    },
    'EL': {
        1: [{'id': 'math1', 'name': 'MATHEMATICS-I'}, {'id': 'phy1', 'name': 'APPLIED PHYSICS-I'}, {'id': 'graphics', 'name': 'ENGG. GRAPHICS'}, {'id': 'chem', 'name': 'APPLIED CHEMISTRY'}, {'id': 'comm_skills', 'name': 'COMM. SKILLS IN ENGLISH'}],
        2: [{'id': 'math2', 'name': 'MATHEMATICS-II'}, {'id': 'phy2', 'name': 'APPLIED PHYSICS-II'}, {'id': 'mechanics', 'name': 'ENGG. MECHANICS'}, {'id': 'it_sys', 'name': 'INTRODUCTION TO IT SYSTEMS'}, {'id': 'eee', 'name': 'FUNDA OF ELECT AND EC ENGG'}],
        3: [{'id': 'em', 'name': 'Electrical machine'}, {'id': 'measurement', 'name': 'Measurement'}, {'id': 'power_gen', 'name': 'power generation'}, {'id': 'fde', 'name': 'Fundamental of basic and digitial electronic'}, {'id': 'circuit', 'name': 'Electric circuit'}],
        4: [{'id': 'power_elec', 'name': 'power electronic'}, {'id': 'td', 'name': 'Tranmision and distribution'}, {'id': 'solar', 'name': 'solar power technology'}, {'id': 'edrive', 'name': 'Electric drive'}, {'id': 'em2', 'name': 'Electric machine 2( Ac machine)'}],
        5: [{'id': 'eca', 'name': 'Energy conservation and audit'}, {'id': 'sgp', 'name': 'Switchgear protection'}, {'id': 'etraction', 'name': 'Electric traction'}, {'id': 'iot', 'name': 'IOT Basic'}, {'id': 'micro', 'name': 'Microprocessor and microcontroller'}],
        6: [{'id': 'uee', 'name': 'Utilisation of electrical energy'}, {'id': 'belect', 'name': 'Building electrification'}, {'id': 'network', 'name': 'Network theory'}, {'id': 'iot_adv', 'name': 'INTERNET OF THINGS (ADVANCE)'}]
    },
    'EE': {
        1: [{'id': 'math2', 'name': 'MATHEMATICS-II'}, {'id': 'phy2', 'name': 'APPLIED PHYSICS-II'}, {'id': 'it_sys', 'name': 'INTRODUCTION TO IT SYSTEMS'}, {'id': 'eee', 'name': 'FUNDAMENTAL OF ELECTRICAL & ELECTRONICS ENGG.'}, {'id': 'mechanics', 'name': 'ENGG. MECHANICS'}],
        2: [{'id': 'math1', 'name': 'MATHEMATICS-I'}, {'id': 'phy1', 'name': 'APPLIED PHYSICS-I'}, {'id': 'chem', 'name': 'APPLIED CHEMISTRY'}, {'id': 'comm_skills', 'name': 'COMMUNICATION SKILLS IN ENGLISH'}, {'id': 'graphics', 'name': 'ENGG. GRAPHICS'}],
        3: [{'id': 'pec', 'name': 'PRINCIPLES OF ELECTRONIC COMMUNICATION'}, {'id': 'edc', 'name': 'ELECTRONIC DEVICES AND CIRCUITS'}, {'id': 'de', 'name': 'DIGITAL ELECTRONICS'}, {'id': 'emi', 'name': 'ELECTRONIC MEASUREMENTS AND INSTRUMENTATION'}, {'id': 'ecn', 'name': 'ELECTRIC CIRCUITS AND NETWORK'}],
        4: [{'id': 'microcontroller', 'name': 'MICROCONTROLLER AND ITS APPLICATIONS'}, {'id': 'consumer_elec', 'name': 'CONSUMER ELECTRONICS'}, {'id': 'dcs', 'name': 'DIGITAL COMMUNICATION SYSTEMS'}, {'id': 'eem', 'name': 'ELECTRONIC EQUIPMENT MAINTENANCE'}, {'id': 'lic', 'name': 'LINEAR INTEGRATED CIRCUITS'}],
        5: [{'id': 'embedded_sys', 'name': 'EMBEDDED SYSTEMS'}, {'id': 'mwc', 'name': 'MOBILE AND WIRELESS COMMUNICATION'}, {'id': 'ind_automation', 'name': 'INDUSTRIAL AUTOMATION'}, {'id': 'microwave_radar', 'name': 'MICROWAVE & RADAR'}, {'id': 'coe1', 'name': 'COE-I'}],
        6: [{'id': 'entrepreneurship', 'name': 'ENTREPRENEURSHIP AND START-UPS'}, {'id': 'cndc', 'name': 'COMPUTER NETWORKING AND DATA COMMUNICATION'}, {'id': 'mechatronics', 'name': 'MECHATRONICS'}, {'id': 'product_design', 'name': 'PRODUCT DESIGN'}, {'id': 'coe2', 'name': 'COE-II'}]
    },
    'ME': {
        1: [{'id': 'math1', 'name': 'MATHEMATICS-I'}, {'id': 'phy1', 'name': 'APPLIED PHYSICS-I'}, {'id': 'chem', 'name': 'APPLIED CHEMISTRY'}, {'id': 'comm_skills', 'name': 'COMMUNICATION SKILLS IN ENGLISH'}, {'id': 'graphics', 'name': 'ENGG. GRAPHICS'}],
        2: [{'id': 'math2', 'name': 'MATHEMATICS-II'}, {'id': 'phy2', 'name': 'APPLIED PHYSICS-II'}, {'id': 'it_sys', 'name': 'INTRODUCTION TO IT SYSTEMS'}, {'id': 'eee', 'name': 'FUNDAMENTAL OF ELECTRICAL & ELECTRONICS ENGG.'}, {'id': 'mechanics', 'name': 'ENGG. MECHANICS'}],
        3: [{'id': 'bme', 'name': 'BASIC MECHANICAL ENGINEERING'}, {'id': 'material_sci', 'name': 'MATERIAL SCIENCE & ENGINEERING'}, {'id': 'fluid_mechanics', 'name': 'FLUID MECHANICS & HYDRAULIC MACHINERY'}, {'id': 'mfg_engg1', 'name': 'MANUFACTURING ENGINEERING- I'}, {'id': 'thermal_engg1', 'name': 'THERMAL ENGINEERING – I'}],
        4: [{'id': 'm_and_m', 'name': 'MEASUREMENTS & METROLOGY'}, {'id': 'som', 'name': 'STRENGTH OF MATERIALS'}, {'id': 'thermal_engg2', 'name': 'THERMAL ENGINEERING- II'}, {'id': 'tomm', 'name': 'THEORY OF MACHINES & MECHANISMS'}, {'id': 'tool_engg', 'name': 'TOOL ENGINEERING'}],
        5: [{'id': 'pom', 'name': 'PRODUCTION & OPERATIONS MANAGEMENT'}, {'id': 'cad_cam', 'name': 'COMPUTER AIDED DESIGN & MANUFACTURING'}, {'id': 'auto_engg', 'name': 'AUTOMOBILE ENGINEERING'}, {'id': 'elective1', 'name': 'ELECTIVE-I'}, {'id': 'coe1', 'name': 'COE-I'}],
        6: [{'id': 'entrepreneurship', 'name': 'ENTREPRENEURSHIP AND START-UPS'}, {'id': 'dme', 'name': 'DESIGN OF MACHINE ELEMENTS'}, {'id': 'adv_mfg_process', 'name': 'ADVANCED MANUFACTURING PROCESSES'}, {'id': 'open_elective1', 'name': 'OPEN ELECTIVE-I'}, {'id': 'coe2', 'name': 'COE-II'}]
    },
    'AE': {
        1: [{'id': 'math1', 'name': 'MATHEMATICS-I'}, {'id': 'phy1', 'name': 'APPLIED PHYSICS-I'}, {'id': 'chem', 'name': 'APPLIED CHEMISTRY'}, {'id': 'comm_skills', 'name': 'COMMUNICATION SKILLS IN ENGLISH'}, {'id': 'graphics', 'name': 'ENGG. GRAPHICS'}],
        2: [{'id': 'math2', 'name': 'MATHEMATICS-II'}, {'id': 'phy2', 'name': 'APPLIED PHYSICS-II'}, {'id': 'it_sys', 'name': 'INTRODUCTION TO IT SYSTEMS'}, {'id': 'eee', 'name': 'FUNDAMENTAL OF ELECTRICAL & ELECTRONICS ENGG.'}, {'id': 'mechanics', 'name': 'ENGG. MECHANICS'}],
        3: [{'id': 'auto_transmission', 'name': 'AUTOMOBILE TRANSMISSION SYSTEM'}, {'id': 'material_sci', 'name': 'MATERIAL SCIENCE & ENGINEERING'}, {'id': 'fluid_mechanics', 'name': 'FLUID MECHANICS & HYDRAULIC MACHINERY'}, {'id': 'vehicle_maintenance', 'name': 'VEHICLE MAINTENANCE'}, {'id': 'thermal_engg1', 'name': 'THERMAL ENGINEERING – I'}],
        4: [{'id': 'auto_engines', 'name': 'AUTOMOBILE ENGINES'}, {'id': 'som', 'name': 'STRENGTH OF MATERIAL'}, {'id': 'auto_system', 'name': 'AUTOMOBILE SYSTEM'}, {'id': 'tomm', 'name': 'THEORY OF MACHINE & MECHANISMS'}, {'id': 'bee', 'name': 'BASIC ELECTRICAL & ELECTRONICS'}],
        5: [{'id': 'adv_auto_engine', 'name': 'ADVANCED AUTOMOBILE ENGINE'}, {'id': 'cad_cam', 'name': 'COMPUTER AIDED DESIGN & MANUFACTURING'}, {'id': 'auto_mfg_process', 'name': 'AUTOMOBILE MANUFACTURING PROCESS'}, {'id': 'auto_elec_sys', 'name': 'AUTOMOTIVE ELECTRICAL & ELECTRONICS SYSTEM'}, {'id': 'coe1', 'name': 'COE-I'}],
        6: [{'id': 'entrepreneurship', 'name': 'ENTREPRENEURSHIP AND START-UPS'}, {'id': 'hybrid_vehicles', 'name': 'HYBRID VEHICLES'}, {'id': 'transport_mgmt', 'name': 'TRANSPORT MANAGEMENT'}, {'id': 'open_elective1', 'name': 'OPEN ELECTIVE-I'}, {'id': 'coe2', 'name': 'COE-II'}]
    }
}
MODELS = {}

def get_ordinal_suffix(sem):
    if 11 <= sem <= 13:
        return 'th'
    if sem % 10 == 1:
        return 'st'
    if sem % 10 == 2:
        return 'nd'
    if sem % 10 == 3:
        return 'rd'
    return 'th'


def load_model(branch, sem):
    model_key = f"{branch}_{sem}"
    if model_key in MODELS:
        return MODELS[model_key]
    
    suffix = get_ordinal_suffix(sem)
    filename = f"student_data_{sem}{suffix}_{branch.lower()}.csv"
    filepath = os.path.join(DATA_FOLDER, filename)

    try:
        raw_data = pd.read_csv(filepath, na_values=['A', 'a'])
        raw_data.fillna(0, inplace=True)
    except FileNotFoundError:
        print(f"WARNING: Data file not found for {branch} Sem {sem} at {filepath}")
        return None
    prev_sem = sem - 1
    prev_subjects = [s['id'] for s in SUBJECTS.get(branch, {}).get(prev_sem, [])]
    curr_subjects = [s['id'] for s in SUBJECTS.get(branch, {}).get(sem, [])]
    required_cols = prev_subjects + [f"{s}_ct" for s in curr_subjects] + ['prev_attendance'] + [f"{s}_final" for s in curr_subjects]
    if not all(col in raw_data.columns for col in required_cols):
        print(f"WARNING: CSV file for {branch} Sem {sem} is missing required columns.")
        return None
    
    
    features = pd.DataFrame()
    features[prev_subjects] = raw_data[prev_subjects]
    for sub in curr_subjects:
        features[f'{sub}_avg'] = raw_data[f'{sub}_ct']
    features['attendance_avg'] = raw_data['prev_attendance']
    features.fillna(0, inplace=True)
    X_train = features

    semester_models = {}
    for sub_info in SUBJECTS.get(branch, {}).get(sem, []):
        sub_id = sub_info['id']
        y_train = raw_data[f'{sub_id}_final']
        model = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_train, y_train)
        semester_models[sub_id] = model
        
    MODELS[model_key] = semester_models
    print(f"Successfully loaded and trained model for {branch} Sem {sem}.")
    return semester_models

# ================== UTILITY & HELPER FUNCTIONS ==================
def time_ago(target_time):
    now = datetime.utcnow()
    time_difference = now - target_time
    seconds = int(time_difference.total_seconds())
    if seconds < 60: return "just now"
    minutes = seconds // 60
    if minutes < 60: return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    hours = minutes // 60
    if hours < 24: return f"{hours} hour{'s' if hours > 1 else ''} ago"
    days = hours // 24
    if days < 7: return f"{days} day{'s' if days > 1 else ''} ago"
    weeks = days // 7
    if weeks < 4: return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    months = days // 30
    if months < 12: return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"

@app.context_processor
def inject_utility_functions():
    return dict(time_ago=time_ago, get_ordinal_suffix=get_ordinal_suffix)

def categorize_level(percentage):
    if percentage > 70: return "Top Performer"
    elif percentage > 60: return "Good"
    elif percentage > 50: return "Average"
    else: return "Below Average"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _save_marks_from_form(form_data, user_id):
    StudentMarks.query.filter_by(user_id=user_id).delete()
    for key, value in form_data.items():
        if value and value.strip():
            try:
                mark_value = float(value)
                new_mark = StudentMarks(user_id=user_id, subject_id=key, marks=mark_value)
                db.session.add(new_mark)
            except (ValueError, TypeError):
                continue
    db.session.commit()

# --- MODIFICATION START: Added helper function for deleting profile pictures ---
def _delete_user_profile_picture(user):
    """Safely deletes a user's profile picture file if it's not a default image."""
    photo_filename = None
    if user.role == 'student' and user.student_info:
        photo_filename = user.student_info.profile_photo
    elif user.role == 'administrator' and user.admin_info:
        photo_filename = user.admin_info.profile_photo

    # --- MODIFICATION START: Updated default paths ---
    default_images = ["images/student_default.png", "images/admin_default.png"]
    # --- MODIFICATION END ---

    if photo_filename and photo_filename not in default_images:
        try:
            # The photo_filename from DB will be like "images/user_1.jpg",
            # os.path.join correctly combines it with the base upload folder path.
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)
                print(f"Successfully deleted profile picture: {photo_path}")
        except Exception as e:
            app.logger.error(f"Error deleting profile picture {photo_filename} for user {user.id}: {e}")


# ================== DECORATORS FOR ROUTE PROTECTION ==================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("role") != role_name:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
    
def student_profile_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        student_info = StudentInfo.query.filter_by(user_id=user_id).first()
        if not student_info:
            flash("Please complete your profile to access this feature.", "warning")
            return redirect(url_for('profile_handler'))
        return f(*args, **kwargs)
    return decorated_function
    
def admin_profile_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
        if not admin_info:
            flash("Please complete your profile to access this feature.", "warning")
            return redirect(url_for('profile_handler'))
        return f(*args, **kwargs)
    return decorated_function

# ================== MAIN & AUTHENTICATION ROUTES ==================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/contact")
def contact():
    """Renders the contact page. The form submission is handled by client-side JavaScript."""
    return render_template("contact.html")

@app.route("/team")
def team():
    return render_template("team.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        role = request.form["role"]
        admin_code_input = request.form.get("admin_code")

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("signup"))
        
        admin_code_setting = Config.query.filter_by(key='admin_code').first()
        correct_admin_code = admin_code_setting.value if admin_code_setting else "1234"

        if role == "administrator" and admin_code_input != correct_admin_code:
            flash("Invalid admin code!", "danger")
            return redirect(url_for("signup"))
        if User.query.filter_by(email=email).first():
            flash("Email already exists! Please log in.", "warning")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password)
        user = User(fullname=fullname, email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        user = User.query.filter_by(email=email, role=role).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            session["user_name"] = user.fullname
            if user.role == "administrator":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("student_dashboard"))
        flash("Invalid credentials or role!", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

# ================== PROFILE ROUTES ==================
@app.route("/profile_handler")
@login_required
def profile_handler():
    user_role = session.get("role")
    return render_template('profile_handler.html', user_role=user_role)

@app.route("/student/profile", methods=["GET", "POST"])
@login_required
@role_required("student")
def profile_student():
    user_id = session["user_id"]
    user = db.session.get(User, user_id)
    student_info = StudentInfo.query.filter_by(user_id=user_id).first()

    if request.method == "POST":
        new_name = request.form["name"]
        reg_no = request.form["reg_no"]
        
        existing_student = StudentInfo.query.filter(StudentInfo.reg_no == reg_no, StudentInfo.user_id != user_id).first()
        if existing_student:
            flash("This registration number is already in use by another student.", "danger")
            return redirect(url_for('profile_student'))
        
        user.fullname = new_name
        session['user_name'] = new_name

        # --- MODIFICATION START: Corrected photo saving and deleting logic ---
        photo_filename_for_db = student_info.profile_photo if student_info else "images/student_default.png"
        
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                
                # Step 1: Delete the old photo if it's not a default one
                if student_info and student_info.profile_photo and student_info.profile_photo not in ["images/student_default.png", "images/admin_default.png"]:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], student_info.profile_photo)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                # Step 2: Save the new photo to the correct folder
                extension = file.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                standard_filename = f"user_{user_id}_{timestamp}.{extension}"
                file.save(os.path.join(PROFILE_IMG_FOLDER, standard_filename))
                
                # Step 3: Set the new filename for the database
                photo_filename_for_db = f"images/{standard_filename}"

        # Update or create the StudentInfo record
        if student_info:
            student_info.name = new_name
            student_info.reg_no = reg_no
            student_info.phone = request.form.get("phone")
            student_info.branch = request.form["branch"]
            student_info.sem = int(request.form["sem"])
            student_info.profile_photo = photo_filename_for_db
        else:
            new_info = StudentInfo(user_id=user_id, name=new_name, reg_no=reg_no,
                                   email=user.email, phone=request.form.get("phone"), branch=request.form["branch"],
                                   sem=int(request.form["sem"]), profile_photo=photo_filename_for_db)
            db.session.add(new_info)
        # --- MODIFICATION END ---
        
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        password_changed = False
        if current_password and new_password and confirm_password:
            if not check_password_hash(user.password, current_password):
                flash("Current password is incorrect. No changes were saved.", "danger")
                return redirect(url_for('profile_student'))
            if new_password != confirm_password:
                flash("New passwords do not match. No changes were saved.", "danger")
                return redirect(url_for('profile_student'))
            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('profile_student'))
            user.password = generate_password_hash(new_password)
            password_changed = True

        db.session.commit()
        
        if password_changed:
            flash("Profile and password updated successfully!", "success")
        else:
            flash("Your profile has been updated successfully!", "success")
            
        return redirect(url_for("student_dashboard"))

    if not student_info:
        student_info = StudentInfo(user_id=user_id, name=user.fullname, profile_photo="images/student_default.png")

    return render_template("profile_student.html", student_info=student_info, user_email=user.email)

@app.route("/admin/profile", methods=["GET", "POST"])
@login_required
@role_required("administrator")
def profile_admin():
    user_id = session["user_id"]
    user = db.session.get(User, user_id)
    admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
    
    if request.method == "POST":
        new_name = request.form["name"]
        user.fullname = new_name
        session['user_name'] = new_name
        
        new_department = request.form.get("department")

        photo_filename_for_db = admin_info.profile_photo if admin_info and admin_info.profile_photo else "images/admin_default.png"
        
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                if admin_info and admin_info.profile_photo and admin_info.profile_photo not in ["images/admin_default.png", "images/student_default.png"]:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], admin_info.profile_photo)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        
                extension = file.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                standard_filename = f"admin_{user_id}_{timestamp}.{extension}"
                file.save(os.path.join(PROFILE_IMG_FOLDER, standard_filename))
                photo_filename_for_db = f"images/{standard_filename}"

        if admin_info:
            admin_info.name = new_name
            admin_info.phone = request.form.get("phone")
            admin_info.department = new_department
            admin_info.profile_photo = photo_filename_for_db
        else:
            new_info = AdminInfo(user_id=user_id, name=new_name,
                                  phone=request.form.get("phone"),
                                  department=new_department,
                                  profile_photo=photo_filename_for_db)
            db.session.add(new_info)
        
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        password_changed = False
        if current_password and new_password and confirm_password:
            if not check_password_hash(user.password, current_password):
                flash("Current password is incorrect. No changes were saved.", "danger")
                return redirect(url_for('profile_admin'))
            if new_password != confirm_password:
                flash("New passwords do not match. No changes were saved.", "danger")
                return redirect(url_for('profile_admin'))
            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('profile_admin'))
            user.password = generate_password_hash(new_password)
            password_changed = True

        current_admin_code = request.form.get("current_admin_code")
        new_admin_code = request.form.get("admin_code")
        confirm_admin_code = request.form.get("confirm_admin_code")
        admin_code_changed = False

        if current_admin_code and new_admin_code and confirm_admin_code:
            admin_code_setting = Config.query.filter_by(key='admin_code').first()
            if not admin_code_setting or current_admin_code != admin_code_setting.value:
                flash("Current Admin Code is incorrect. No changes were saved.", "danger")
                return redirect(url_for('profile_admin'))
            if new_admin_code != confirm_admin_code:
                flash("New admin codes do not match. No changes were saved.", "danger")
                return redirect(url_for('profile_admin'))
            admin_code_setting.value = new_admin_code
            admin_code_changed = True

        db.session.commit()
        
        if password_changed and admin_code_changed:
            flash("Profile, password, and admin code updated successfully!", "success")
        elif password_changed:
            flash("Profile and password updated successfully!", "success")
        elif admin_code_changed:
            flash("Profile and admin code updated successfully!", "success")
        else:
            flash("Your profile has been updated successfully!", "success")
            
        return redirect(url_for("admin_dashboard"))

    super_admin_code_setting = Config.query.filter_by(key='super_admin_code').first()
    super_admin_code = super_admin_code_setting.value if super_admin_code_setting else "5678"
    return render_template("profile_admin.html", admin_info=admin_info, user_email=user.email, super_admin_code=super_admin_code)

# ================== ADMIN ROUTES ==================
@app.route("/admin/dashboard")
@login_required
@role_required("administrator")
def admin_dashboard():
    user_name = session.get("user_name", "Admin")
    user_id = session.get("user_id")
    admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
    if not admin_info:
        flash("Please complete your profile to access all features.", "warning")
    return render_template("admin_dashboard.html", user_name=user_name)

@app.route("/admin/registered_users")
@login_required
@role_required("administrator")
@admin_profile_required
def registered_users():
    user_id = session['user_id']
    admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
    is_super_admin = admin_info and admin_info.department == 'ALL_BRANCHES'
    admin_department = admin_info.department if admin_info else "ALL_BRANCHES"

    view_as = request.args.get('view_as', 'students') 
    sort_by = request.args.get('sort_by', 'name')
    search_query = request.args.get('search', '')
    selected_branch = request.args.get('branch', admin_department)

    students = []
    admin_users = []

    if view_as == 'students':
        query = StudentInfo.query
        if is_super_admin and selected_branch.upper() != "ALL_BRANCHES":
            query = query.filter_by(branch=selected_branch)
        elif not is_super_admin:
            query = query.filter_by(branch=admin_department)
        
        if sort_by == 'name':
            query = query.order_by(db.func.lower(StudentInfo.name).asc())
        elif sort_by == 'reg_no':
            query = query.order_by(cast(StudentInfo.reg_no, Integer).asc())
        elif sort_by == 'sem':
            query = query.order_by(StudentInfo.sem.asc())
        else:
            query = query.order_by(db.func.lower(StudentInfo.name).asc())
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                db.or_(
                    StudentInfo.name.ilike(search_pattern),
                    StudentInfo.reg_no.ilike(search_pattern)
                )
            )

        students = query.all()

    elif view_as == 'admins' and is_super_admin:
        query = db.session.query(AdminInfo).options(joinedload(AdminInfo.user))
        
        if sort_by == 'name':
            query = query.order_by(db.func.lower(AdminInfo.name).asc())
        elif sort_by == 'department':
            query = query.order_by(db.func.lower(AdminInfo.department).asc())
        elif sort_by == 'phone':
            query = query.order_by(AdminInfo.phone.asc())
        else:
            query = query.order_by(db.func.lower(AdminInfo.name).asc())
            
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                db.or_(
                    AdminInfo.name.ilike(search_pattern),
                    AdminInfo.department.ilike(search_pattern)
                )
            )

        admin_users = query.all()

    all_branches_map = {key: key for key in sorted(list(SUBJECTS.keys()))}
    
    return render_template(
        "registered_users.html", 
        students=students, 
        admin_users=admin_users, 
        admin_department=admin_department, 
        sort_by=sort_by, 
        is_super_admin=is_super_admin, 
        all_branches_map=all_branches_map, 
        selected_branch=selected_branch,
        search_query=search_query,
        view_as=view_as
    )

@app.route('/admin/search_users_dynamic')
@login_required
@role_required("administrator")
@admin_profile_required
def search_users_dynamic():
    user_id = session['user_id']
    admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
    is_super_admin = admin_info and admin_info.department == 'ALL_BRANCHES'
    admin_department = admin_info.department if admin_info else "ALL_BRANCHES"

    view_as = request.args.get('view_as', 'students')
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    selected_branch = request.args.get('branch', admin_department)

    results = []

    if view_as == 'students':
        query = StudentInfo.query
        if is_super_admin and selected_branch.upper() != "ALL_BRANCHES":
            query = query.filter_by(branch=selected_branch)
        elif not is_super_admin:
            query = query.filter_by(branch=admin_department)
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                db.or_(
                    StudentInfo.name.ilike(search_pattern),
                    StudentInfo.reg_no.ilike(search_pattern)
                )
            )

        if sort_by == 'name':
            query = query.order_by(db.func.lower(StudentInfo.name).asc())
        elif sort_by == 'reg_no':
            query = query.order_by(cast(StudentInfo.reg_no, Integer).asc())
        elif sort_by == 'sem':
            query = query.order_by(StudentInfo.sem.asc())
        else:
            query = query.order_by(db.func.lower(StudentInfo.name).asc())
        
        students = query.all()
        for s in students:
            results.append({
                'id': s.user_id,
                'name': s.name,
                'reg_no': s.reg_no,
                'branch': s.branch,
                'sem': s.sem,
                'email': s.email,
                'profile_photo': s.profile_photo if s.profile_photo else 'student_default.png',
                'edit_url': url_for('edit_student_info', user_id=s.user_id),
                'analytics_url': url_for('student_analytics', user_id=s.user_id),
                'delete_url': url_for('delete_student', user_id=s.user_id),
            })

    elif view_as == 'admins' and is_super_admin:
        query = db.session.query(AdminInfo).options(joinedload(AdminInfo.user))

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                db.or_(
                    AdminInfo.name.ilike(search_pattern),
                    AdminInfo.department.ilike(search_pattern)
                )
            )

        if sort_by == 'name':
            query = query.order_by(db.func.lower(AdminInfo.name).asc())
        elif sort_by == 'department':
            query = query.order_by(db.func.lower(AdminInfo.department).asc())
        elif sort_by == 'phone':
            query = query.order_by(AdminInfo.phone.asc())
        else:
            query = query.order_by(db.func.lower(AdminInfo.name).asc())

        admin_users = query.all()
        for a in admin_users:
            results.append({
                'id': a.user_id,
                'name': a.name,
                'department': a.department,
                'phone': a.phone,
                'email': a.user.email,
                'profile_photo': a.profile_photo if a.profile_photo else 'admin_default.png',
                'edit_url': url_for('edit_admin_info', user_id=a.user_id),
                'delete_url': url_for('delete_admin', user_id=a.user_id),
            })
    
    return jsonify(results=results)

@app.route("/admin/admins/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def edit_admin_info(user_id):
    admin_to_edit_info = AdminInfo.query.filter_by(user_id=user_id).first_or_404()
    admin_to_edit_user = User.query.filter_by(id=user_id).first_or_404()
    
    current_admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
    is_super_admin = current_admin_info and current_admin_info.department == 'ALL_BRANCHES'
    
    if not is_super_admin:
        flash("You are not authorized to edit this administrator's profile.", "danger")
        return redirect(url_for('registered_users'))
        
    if request.method == "POST":
        new_name = request.form["name"]
        new_phone = request.form.get("phone")
        new_department = request.form["department"]
        
        if new_department == 'ALL_BRANCHES' and not is_super_admin:
            flash("You are not authorized to set a department to 'ALL_BRANCHES'.", "danger")
            return redirect(url_for('edit_admin_info', user_id=user_id))
            
        admin_to_edit_user.fullname = new_name
        admin_to_edit_info.name = new_name
        admin_to_edit_info.phone = new_phone
        admin_to_edit_info.department = new_department

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                if admin_to_edit_info.profile_photo and admin_to_edit_info.profile_photo not in ["images/admin_default.png", "images/student_default.png"]:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], admin_to_edit_info.profile_photo)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                extension = file.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                standard_filename = f"admin_{user_id}_{timestamp}.{extension}"
                file.save(os.path.join(PROFILE_IMG_FOLDER, standard_filename))
                
                admin_to_edit_info.profile_photo = f"images/{standard_filename}"
        
        db.session.commit()
        flash("Administrator profile updated successfully!", "success")
        return redirect(url_for('registered_users', view_as='admins'))
    
    all_branches = list(SUBJECTS.keys())
    return render_template('reg_adm_edit.html', admin=admin_to_edit_info, is_super_admin=is_super_admin, all_branches=all_branches, user=admin_to_edit_user)


@app.route("/admin/admins/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def delete_admin(user_id):
    current_admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
    is_super_admin = current_admin_info and current_admin_info.department == 'ALL_BRANCHES'
    
    user_to_delete = User.query.filter_by(id=user_id).first_or_404()
    
    if not is_super_admin:
        flash("You are not authorized to delete other administrators.", "danger")
        return redirect(url_for('registered_users', view_as='admins'))
        
    target_admin_info = AdminInfo.query.filter_by(user_id=user_to_delete.id).first()
    if target_admin_info and target_admin_info.department == 'ALL_BRANCHES':
        flash("You cannot delete a super administrator.", "danger")
        return redirect(url_for('registered_users', view_as='admins'))
        
    if user_to_delete.id == session['user_id']:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('registered_users', view_as='admins'))

    _delete_user_profile_picture(user_to_delete)

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"Administrator '{user_to_delete.fullname}' and all associated data have been deleted.", "success")
    return redirect(url_for('registered_users', view_as='admins'))


@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def edit_student_info(user_id):
    student_info = StudentInfo.query.filter_by(user_id=user_id).first_or_404()
    user = User.query.filter_by(id=user_id).first_or_404()
    
    if request.method == "POST":
        new_name = request.form["name"]
        reg_no = request.form["reg_no"]
        new_phone = request.form.get("phone")
        new_branch = request.form["branch"]
        new_sem = int(request.form["sem"])
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        existing_student = StudentInfo.query.filter(StudentInfo.reg_no == reg_no, StudentInfo.user_id != user_id).first()
        if existing_student:
            flash("This registration number is already in use by another student.", "danger")
            return redirect(url_for('edit_student_info', user_id=user_id))

        user.fullname = new_name
        
        student_info.name = new_name
        student_info.reg_no = reg_no
        student_info.phone = new_phone
        student_info.branch = new_branch
        student_info.sem = new_sem
        
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                
                if student_info.profile_photo and student_info.profile_photo not in ["images/student_default.png", "images/admin_default.png"]:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], student_info.profile_photo)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                extension = file.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                standard_filename = f"user_{user_id}_{timestamp}.{extension}"
                file.save(os.path.join(PROFILE_IMG_FOLDER, standard_filename))

                student_info.profile_photo = f"images/{standard_filename}"
        
        if new_password and new_password.strip():
            if new_password != confirm_password:
                flash("New passwords do not match. No password was updated.", "danger")
                return redirect(url_for('edit_student_info', user_id=user_id))
            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return redirect(url_for('edit_student_info', user_id=user_id))
            user.password = generate_password_hash(new_password)
            flash("Student profile and password updated successfully!", "success")
        else:
            flash("Student profile updated successfully!", "success")

        db.session.commit()
        return redirect(url_for('registered_users'))

    return render_template('reg_stu_edit.html', student=student_info)

@app.route("/admin/users/analytics/<int:user_id>")
@login_required
@role_required("administrator")
@admin_profile_required
def student_analytics(user_id):
    student_info = StudentInfo.query.filter_by(user_id=user_id).first_or_404()
    branch, sem = student_info.branch, student_info.sem
    
    semester_models = load_model(branch, sem)
    if not semester_models:
        return render_template("admin_analytics_handler.html", branch=branch, sem=sem)

    prev_subjects = SUBJECTS.get(branch, {}).get(sem - 1, [])
    current_subjects = SUBJECTS.get(branch, {}).get(sem, [])
    saved_marks_all = {mark.subject_id: mark.marks for mark in StudentMarks.query.filter_by(user_id=user_id).all()}

    prev_sem_marks = {s['id']: saved_marks_all.get(s['id']) for s in prev_subjects}
    current_ct_marks = {k: v for k, v in saved_marks_all.items() if '_ct' in k}
    attendance_marks = {k: v for k, v in saved_marks_all.items() if k.startswith('prev_attendance_')}

    predictions, avg_score, level, tips = None, None, None, None

    if saved_marks_all:
        try:
            model_key = f"{branch}_{sem}"
            sample_model = list(MODELS[model_key].values())[0]
            feature_names = sample_model.feature_names_in_

            input_data = {}
            for name in feature_names:
                if name == 'attendance_avg':
                    attendance_values = [v for k, v in saved_marks_all.items() if k.startswith('prev_attendance_')]
                    input_data[name] = sum(attendance_values) / len(attendance_values) if attendance_values else 0
                elif name == 'attendance_count':
                    input_data[name] = 1 if any(k.startswith('prev_attendance_') for k in saved_marks_all) else 0
                elif name.endswith('_avg'):
                    sub_id = name[:-4]
                    ct_marks = [v for k, v in saved_marks_all.items() if k.startswith(f'{sub_id}_ct_')]
                    input_data[name] = sum(ct_marks) / len(ct_marks) if ct_marks else 0
                elif name.endswith('_count'):
                    input_data[name] = 1 if any(k.startswith(f'{sub_id}_ct_') for k in saved_marks_all) else 0
                else:
                    input_data[name] = saved_marks_all.get(name, 0)
            
            input_df = pd.DataFrame([input_data])[feature_names]

            raw_predictions = {
                s['name']: round(max(0, min(70, semester_models[s['id']].predict(input_df)[0])))
                for s in current_subjects
            }

            # PIE CHART MODIFICATION START
            total_predicted_marks = sum(raw_predictions.values())
            predictions = {}
            for subject, mark in raw_predictions.items():
                percentage = (mark / total_predicted_marks) * 100 if total_predicted_marks > 0 else 0
                predictions[subject] = {
                    "mark": mark,
                    "level": categorize_level((mark / 70) * 100),
                    "percentage": round(percentage, 2)
                }
            # PIE CHART MODIFICATION END

            avg_score = round(sum(raw_predictions.values()) / len(raw_predictions), 2) if raw_predictions else 0
            level = categorize_level((avg_score / 70) * 100)
            tips = "Focus on weaker areas for improvement." if avg_score < 60 else "Keep up the great work!"
        except Exception as e:
            app.logger.error(f"Prediction error on page load for user {user_id}: {e}")
            flash("Could not generate a prediction with the saved marks.", "warning")

             # --- NEW CODE FOR ATTENDANCE PROJECTION START ---
    projected_attendance = {}
    if attendance_marks:
        # Get the keys (e.g., 'prev_attendance_1'), sort them numerically, and get the last one
        last_attendance_key = sorted(attendance_marks.keys(), key=lambda k: int(k.split('_')[-1]))[-1]
        last_attendance_value = attendance_marks[last_attendance_key]
        
        # Project the next semester's attendance to be the same as the last
        last_sem_num = int(last_attendance_key.split('_')[-1])
        projected_attendance[f"Semester {last_sem_num + 1} (Proj.)"] = last_attendance_value
    # --- NEW CODE FOR ATTENDANCE PROJECTION END ---


    return render_template(
        'reg_stu_analytics.html', 
        student_info=student_info,
        prev_subjects=prev_subjects,
        current_subjects=current_subjects,
        prev_sem_marks=prev_sem_marks,
        current_ct_marks=current_ct_marks,
        attendance_marks=attendance_marks,
        predictions=predictions,
        avg_score=avg_score,
        level=level,
        tips=tips,
        projected_attendance=projected_attendance # <-- ADD THIS
    )

@app.route("/admin/users/predict/<int:user_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_predict(user_id):
    student_info = StudentInfo.query.filter_by(user_id=user_id).first_or_404()
    
    branch, sem = student_info.branch, student_info.sem
    if not load_model(branch, sem):
        return render_template("admin_analytics_handler.html", branch=branch, sem=sem)

    _save_marks_from_form(request.form, user_id)
    flash("Marks saved successfully. Prediction has been updated.", "success")
    return redirect(url_for('student_analytics', user_id=user_id))

@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def delete_student(user_id):
    user_to_delete = User.query.filter_by(id=user_id).first_or_404()
    
    _delete_user_profile_picture(user_to_delete)
    
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"User '{user_to_delete.fullname}' and all associated data have been deleted.", "success")
    return redirect(url_for('registered_users'))

@app.route("/admin/material_uploader", methods=['GET', 'POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def material_uploader():
    user_id = session.get("user_id")
    admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
    admin_department = admin_info.department if admin_info else "ALL_BRANCHES"

    if request.method == 'POST':
        file = request.files.get('file')
        subject_id = request.form.get('subject_id')
        if not file or not subject_id or not file.filename:
            flash("Please provide both a file and a subject.", "danger")
            return redirect(url_for('material_uploader'))

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(NOTES_FOLDER, filename)
            file.save(filepath)

            new_note = StudyMaterial(subject_id=subject_id, file_name=filename, user_id=user_id)
            db.session.add(new_note)
            db.session.commit()
            flash(f"File '{filename}' uploaded successfully!", "success")
        else:
            flash("Invalid file type. Allowed types are: png, jpg, jpeg, gif, pdf, docx, pptx.", "danger")
        return redirect(url_for("material_uploader"))

    uploaded_notes = StudyMaterial.query.options(joinedload(StudyMaterial.uploader_user)).order_by(StudyMaterial.upload_date.desc()).all()
    uploaded_csvs = AnalyticsFile.query.options(joinedload(AnalyticsFile.uploader_user)).order_by(AnalyticsFile.upload_date.desc()).all()
    
    return render_template("admin_material_uploader.html", 
                           notes=uploaded_notes, 
                           all_subjects_dict=SUBJECTS,
                           uploaded_csvs=uploaded_csvs,
                           admin_department=admin_department)

@app.route('/admin/download_analytics_template')
@login_required
@role_required("administrator")
@admin_profile_required
def download_analytics_template():
    """Generates and serves a blank CSV template with correct headers."""
    branch = request.args.get('branch')
    sem_str = request.args.get('sem')

    if not branch or not sem_str:
        flash("Please select both a branch and a semester first.", "warning")
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))

    try:
        sem = int(sem_str)
        if not (1 <= sem <= 6):
             raise ValueError("Semester out of range")
    except (ValueError, TypeError):
        flash("Invalid semester selected.", "danger")
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))

    # Get subject IDs for the previous and current semester
    prev_sem = sem - 1
    prev_subjects = [s['id'] for s in SUBJECTS.get(branch, {}).get(prev_sem, [])]
    curr_subjects = [s['id'] for s in SUBJECTS.get(branch, {}).get(sem, [])]

    # Ensure there are 5 subjects for each, pad if necessary (for robustness)
    while len(prev_subjects) < 5:
        prev_subjects.append(f'prev_subject_{len(prev_subjects)+1}_placeholder')
    while len(curr_subjects) < 5:
        curr_subjects.append(f'curr_subject_{len(curr_subjects)+1}_placeholder')

    # Construct the exact header list the model expects (16 columns)
    headers = (
        prev_subjects[:5] +
        [f"{s}_ct" for s in curr_subjects[:5]] +
        ['prev_attendance'] +
        [f"{s}_final" for s in curr_subjects[:5]]
    )

    # Create a blank DataFrame and then a CSV in memory
    df = pd.DataFrame(columns=headers)
    
    buffer = io.BytesIO()
    buffer.write(df.to_csv(index=False).encode('utf-8'))
    buffer.seek(0)
    
    suffix = get_ordinal_suffix(sem)
    filename = f"template_{branch}_{sem}{suffix}_sem.csv"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

@app.route('/admin/upload_analytics_data', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def upload_analytics_data():
    branch = request.form.get('branch')
    sem_str = request.form.get('sem')
    file = request.files.get('file')
    user_id = session.get("user_id")

    if not all([branch, sem_str, file, file.filename]):
        flash('Missing branch, semester, or file.', 'danger')
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))

    file_extension = file.filename.rsplit('.', 1)[1].lower()
    if file_extension not in ['csv', 'xlsx']:
        flash('Invalid file type. Please upload a CSV or Excel file.', 'danger')
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))

    sem = int(sem_str)
    try:
        # --- MODIFICATION START: Header validation logic ---
        # 1. Generate the list of expected headers for the selected branch/semester
        prev_sem = sem - 1
        prev_subjects = [s['id'] for s in SUBJECTS.get(branch, {}).get(prev_sem, [])]
        curr_subjects = [s['id'] for s in SUBJECTS.get(branch, {}).get(sem, [])]

        while len(prev_subjects) < 5:
            prev_subjects.append(f'prev_subject_{len(prev_subjects)+1}_placeholder')
        while len(curr_subjects) < 5:
            curr_subjects.append(f'curr_subject_{len(curr_subjects)+1}_placeholder')

        expected_headers = (
            prev_subjects[:5] +
            [f"{s}_ct" for s in curr_subjects[:5]] +
            ['prev_attendance'] +
            [f"{s}_final" for s in curr_subjects[:5]]
        )
        # --- MODIFICATION END ---

        if file_extension == 'csv':
            try:
                df = pd.read_csv(file)
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_csv(file, encoding='latin-1')
        else: # xlsx
            df = pd.read_excel(file)

        # --- MODIFICATION START: Compare actual headers with expected headers ---
        actual_headers = df.columns.tolist()
        if actual_headers != expected_headers:
            flash(f'Upload failed: The file columns do not match the required template for {branch} Semester {sem}. Please download and use the correct template.', 'danger')
            return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))
        # --- MODIFICATION END ---
        
        file.seek(0)

        suffix = get_ordinal_suffix(sem)
        filename = f"student_data_{sem}{suffix}_{branch.lower()}.csv"
        filepath = os.path.join(DATA_FOLDER, filename)
        
        df.to_csv(filepath, index=False)
        
        model_key = f"{branch}_{sem}"
        if model_key in MODELS:
            del MODELS[model_key]
            print(f"SUCCESS: Invalidated cached model for {branch} Semester {sem}.")

        existing_file = AnalyticsFile.query.filter_by(file_name=filename).first()
        if existing_file:
            existing_file.user_id = user_id
            existing_file.upload_date = datetime.utcnow()
        else:
            new_file_record = AnalyticsFile(file_name=filename, user_id=user_id)
            db.session.add(new_file_record)
        db.session.commit()
        
        flash(f'Successfully uploaded and validated analytics data for {branch} Semester {sem}.', 'success')
    
    except pd.errors.ParserError as e:
        flash(f"CSV/Excel Formatting Error: {e}. Please check your file for issues like extra commas or incorrect line breaks.", 'danger')
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))
    except ImportError:
        flash("Processing Excel files requires the 'openpyxl' library. Please install it by running 'pip install openpyxl' in your terminal.", 'danger')
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))
    except Exception as e:
        flash(f'An unexpected error occurred while processing the file: {e}', 'danger')
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))
    
    return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))


@app.route("/admin/delete_note/<int:note_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def delete_note(note_id):
    note = db.session.get(StudyMaterial, note_id)
    if note:
        admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
        if admin_info.department == 'ALL_BRANCHES' or note.user_id == session['user_id']:
            try:
                filepath = os.path.join(NOTES_FOLDER, note.file_name)
                if os.path.exists(filepath):
                    os.remove(filepath)
                db.session.delete(note)
                db.session.commit()
                flash("Note deleted successfully.", "success")
            except Exception as e:
                flash(f"Error deleting note file: {e}", "danger")
                db.session.rollback()
        else:
            flash("You are not authorized to delete this note.", "danger")
    else:
        flash("Note not found.", "danger")
    return redirect(url_for("material_uploader"))

@app.route("/admin/announcements", methods=["GET", "POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_announcements():
    user_id = session.get("user_id")
    current_admin_info = AdminInfo.query.filter_by(user_id=user_id).first()
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        department = request.form.get("department")
        semester_str = request.form.get("semester")
        semester = int(semester_str) if semester_str and semester_str.isdigit() else 0
        
        uploaded_files = request.files.getlist('files[]')
        filenames = []
        
        for file in uploaded_files:
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(ANNOUNCEMENTS_FOLDER, filename)
                    file.save(file_path)
                    filenames.append(filename)
                else:
                    flash(f"Invalid file type for {file.filename}.", "danger")
        
        attached_files_string = ','.join(filenames) if filenames else None
        
        if title and content and department:
            announcement = Announcement(
                title=title,
                content=content,
                user_id=user_id,
                department=department,
                semester=semester,
                attached_files=attached_files_string
            )
            db.session.add(announcement)
            db.session.commit()
            flash("Announcement posted successfully!", "success")
        else:
            flash("Title, content, and department cannot be empty.", "danger")
        return redirect(url_for("admin_announcements"))

    all_announcements = db.session.query(Announcement).options(db.joinedload(Announcement.user)).order_by(Announcement.timestamp.desc()).all()
    admin_department = current_admin_info.department if current_admin_info else "ALL_BRANCHES"
    all_branches = list(SUBJECTS.keys())

    return render_template("admin_announcements.html", announcements=all_announcements, admin_department=admin_department, all_branches=all_branches, current_admin_info=current_admin_info)

@app.route("/admin/announcements/edit/<int:announcement_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def edit_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)

    if announcement.user_id != session['user_id']:
        flash("You are not authorized to edit this announcement.", "danger")
        return redirect(url_for("admin_announcements"))

    title = request.form.get("title")
    content = request.form.get("content")
    
    if not title or not content:
        flash("Title and content cannot be empty.", "danger")
        return redirect(url_for("admin_announcements"))

    changes_made = False

    if title != announcement.title or content != announcement.content:
        announcement.title = title
        announcement.content = content
        announcement.edited = True
        changes_made = True

    uploaded_files = request.files.getlist('files[]')
    
    if any(file.filename for file in uploaded_files):
        if announcement.attached_files:
            for file_name in announcement.attached_files.split(','):
                file_path = os.path.join(ANNOUNCEMENTS_FOLDER, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)

        new_filenames = []
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(ANNOUNCEMENTS_FOLDER, filename)
                file.save(file_path)
                new_filenames.append(filename)
            elif file.filename != '':
                flash(f"Invalid file type for {file.filename}.", "danger")
                return redirect(url_for("admin_announcements"))
        
        announcement.attached_files = ','.join(new_filenames) if new_filenames else None
        announcement.edited = True
        changes_made = True

    if changes_made:
        db.session.commit()
        flash("Announcement updated successfully.", "success")
    else:
        flash("No changes were made to the announcement.", "info")

    return redirect(url_for("admin_announcements"))

@app.route("/admin/announcements/delete/<int:announcement_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
    is_super_admin = admin_info and admin_info.department == 'ALL_BRANCHES'

    if is_super_admin or announcement.user_id == session['user_id']:
        try:
            if announcement.attached_files:
                announcements_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'announcements')
                for file_name in announcement.attached_files.split(','):
                    file_path = os.path.join(announcements_folder, file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

            db.session.delete(announcement)
            db.session.commit()
            flash("Announcement deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting announcement: {e}", "danger")
            db.session.rollback()
    else:
        flash("You are not authorized to delete this announcement.", "danger")
    
    return redirect(url_for("admin_announcements"))
    
@app.route("/admin/query_solver", methods=["GET", "POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def query_solver():
    user_id = session['user_id']
    user = db.session.get(User, user_id)

    if request.method == "POST":
        if user.is_forum_blocked:
            blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
            flash(f"You have been blocked from the forum by {blocker_name}. Please contact them for assistance.", "blocked")
            return redirect(url_for('query_solver'))

        query_text = request.form.get("query_text")
        if query_text and query_text.strip():
            db.session.add(Query(text=query_text, user_id=user_id))
            db.session.commit()
            flash("Your query has been posted successfully!", "success")
        return redirect(url_for('query_solver'))

    queries_query = db.session.query(Query).options(
        subqueryload(Query.replies).joinedload(Reply.author).joinedload(User.student_info),
        subqueryload(Query.replies).joinedload(Reply.author).joinedload(User.admin_info),
        subqueryload(Query.replies).subqueryload(Reply.hearts).joinedload(Heart.author),
        joinedload(Query.author).joinedload(User.admin_info),
        joinedload(Query.author).joinedload(User.student_info),
        subqueryload(Query.hearts).joinedload(Heart.author)
    ).all()

    queries_query.sort(key=lambda q: (q.is_pinned, q.author.role == 'administrator', q.timestamp), reverse=True)

    for query in queries_query:
        query.user_vote = QueryVote.query.filter_by(user_id=user_id, query_id=query.id).first()
        query.user_heart = Heart.query.filter_by(user_id=user_id, query_id=query.id).first()
        for reply in query.replies:
            reply.user_vote = ReplyVote.query.filter_by(user_id=user_id, reply_id=reply.id).first()
            reply.user_heart = Heart.query.filter_by(user_id=user_id, reply_id=reply.id).first()
    
    chat_lock_status = Config.query.filter_by(key='is_chat_locked').first()
    is_chat_locked = (chat_lock_status.value == 'true') if chat_lock_status else False
    current_admin_info = AdminInfo.query.filter_by(user_id=user_id).first()

    return render_template(
        "query_solver.html", 
        queries=queries_query, 
        is_chat_locked=is_chat_locked, 
        current_admin_info=current_admin_info,
        current_user=user
    )

@app.route('/admin/preview_analytics_data/<filename>')
@login_required
@role_required("administrator")
@admin_profile_required
def preview_analytics_data(filename):
    filepath = os.path.join(DATA_FOLDER, filename)
    try:
        df = pd.read_csv(filepath)
        headers = df.columns.tolist()
        rows = df.values.tolist()
        return jsonify({'headers': headers, 'rows': rows})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/admin/delete_analytics_data/<filename>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def delete_analytics_data(filename):
    admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
    file_record = AnalyticsFile.query.filter_by(file_name=filename).first()
    
    if not (admin_info.department == 'ALL_BRANCHES' or (file_record and file_record.user_id == session['user_id'])):
        flash("You are not authorized to delete this file.", "danger")
        return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))

    try:
        filepath = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
            if file_record:
                db.session.delete(file_record)
                db.session.commit()

            flash(f'File {filename} deleted successfully.', 'success')
        else:
            flash('File not found.', 'danger')
    except Exception as e:
        flash(f'Error deleting file: {e}', 'danger')
    return redirect(url_for('material_uploader', _anchor='analytics-tab-pane'))

@app.route('/admin/download_analytics_data/<filename>')
@login_required
@role_required("administrator")
@admin_profile_required
def download_analytics_data(filename):
    return send_from_directory(DATA_FOLDER, filename, as_attachment=True)

@app.route('/admin/post_reply/<int:query_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_post_reply(query_id):
    user = db.session.get(User, session['user_id'])
    if user.is_forum_blocked:
        blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
        flash(f"You have been blocked from the forum by {blocker_name}. Please contact them for assistance.", "blocked")
        return redirect(url_for('query_solver'))
        
    reply_text = request.form.get("reply_text")
    parent_id = request.form.get("parent_id")
    
    if reply_text and reply_text.strip() and Query.query.get(query_id):
        new_reply = Reply(
            text=reply_text, 
            user_id=session['user_id'], 
            query_id=query_id,
            parent_id=int(parent_id) if parent_id and parent_id.isdigit() else None
        )
        db.session.add(new_reply)
        db.session.commit()
        flash("Your reply has been posted.", "success")
        return redirect(url_for('query_solver', _anchor=f'reply-{new_reply.id}'))
    return redirect(url_for('query_solver'))

@app.route('/admin/delete_query/<int:query_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_delete_query(query_id):
    user = db.session.get(User, session['user_id'])
    if user.is_forum_blocked:
        blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
        flash(f"You cannot perform this action because you have been blocked by {blocker_name}.", "blocked")
        return redirect(url_for('query_solver'))

    query = db.session.get(Query, query_id)
    if not query:
        flash("Query not found.", "danger")
        return redirect(url_for('query_solver'))

    current_admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
    is_super_admin = current_admin_info and current_admin_info.department == 'ALL_BRANCHES'

    if is_super_admin or query.author.role == 'student' or session['user_id'] == query.user_id:
        db.session.delete(query)
        db.session.commit()
        flash("Query has been deleted.", "success")
    else:
        flash("You are not authorized to delete this query.", "danger")
    
    return redirect(url_for('query_solver'))

@app.route('/admin/delete_reply/<int:reply_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_delete_reply(reply_id):
    user = db.session.get(User, session['user_id'])
    if user.is_forum_blocked:
        blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
        flash(f"You cannot perform this action because you have been blocked by {blocker_name}.", "blocked")
        return redirect(url_for('query_solver'))

    reply = db.session.get(Reply, reply_id)
    if not reply:
        flash("Reply not found.", "danger")
        return redirect(url_for('query_solver'))
        
    current_admin_info = AdminInfo.query.filter_by(user_id=session['user_id']).first()
    is_super_admin = current_admin_info and current_admin_info.department == 'ALL_BRANCHES'

    if is_super_admin or reply.author.role == 'student' or session['user_id'] == reply.user_id:
        db.session.delete(reply)
        db.session.commit()
        flash("Reply has been deleted.", "success")
    else:
        flash("You are not authorized to delete this reply.", "danger")
        
    return redirect(url_for('query_solver'))

@app.route('/admin/toggle_pin/<string:entity_type>/<int:entity_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_toggle_pin(entity_type, entity_id):
    user = db.session.get(User, session['user_id'])
    if user.is_forum_blocked:
        blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
        flash(f"You cannot perform this action because you have been blocked by {blocker_name}.", "blocked")
        return redirect(url_for('query_solver'))

    if entity_type == 'query':
        item = db.session.get(Query, entity_id)
    else:
        item = db.session.get(Reply, entity_id)
    
    if item:
        item.is_pinned = not item.is_pinned
        db.session.commit()
        flash(f"{entity_type.capitalize()} has been {'pinned' if item.is_pinned else 'unpinned'}.", "success")
    return redirect(url_for('query_solver'))

@app.route('/admin/toggle_lock/<int:query_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_toggle_lock(query_id):
    query = db.session.get(Query, query_id)
    if query:
        query.is_locked = not query.is_locked
        db.session.commit()
        flash(f"Query has been {'locked' if query.is_locked else 'unlocked'}.", "success")
    return redirect(url_for('query_solver'))

@app.route('/admin/toggle_forum_block/<int:user_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def toggle_forum_block(user_id):
    current_user_id = session['user_id']
    current_user = db.session.get(User, current_user_id)

    if current_user.is_forum_blocked:
        blocker_name = current_user.blocker.fullname if current_user.blocker else "a Super Admin"
        flash(f"You cannot perform this action because you have been blocked by {blocker_name}.", "blocked")
        return redirect(url_for('query_solver'))

    user_to_block = db.session.get(User, user_id)

    if not user_to_block:
        flash("User not found.", "danger")
        return redirect(request.referrer or url_for('query_solver'))

    if user_to_block.id == current_user_id:
        flash("You cannot block yourself.", "warning")
        return redirect(request.referrer or url_for('query_solver'))

    current_admin_info = AdminInfo.query.filter_by(user_id=current_user_id).first()
    is_super_admin = current_admin_info and current_admin_info.department == 'ALL_BRANCHES'
    
    can_block = False
    
    if user_to_block.role == 'student':
        can_block = True
    elif user_to_block.role == 'administrator':
        if is_super_admin:
            target_admin_info = AdminInfo.query.filter_by(user_id=user_to_block.id).first()
            is_target_super_admin = target_admin_info and target_admin_info.department == 'ALL_BRANCHES'
            
            if not is_target_super_admin:
                can_block = True
            else:
                flash("A super admin cannot block another super admin.", "danger")
        else:
            flash("You are not authorized to block another administrator.", "danger")
    else:
        flash("This user cannot be blocked.", "danger")

    if can_block:
        user_to_block.is_forum_blocked = not user_to_block.is_forum_blocked
        if user_to_block.is_forum_blocked:
            user_to_block.blocked_by_id = current_user_id
        else:
            user_to_block.blocked_by_id = None
            
        db.session.commit()
        flash(f"User '{user_to_block.fullname}' has been {'blocked' if user_to_block.is_forum_blocked else 'unblocked'}.", "success")
    
    return redirect(request.referrer or url_for('query_solver'))

@app.route('/admin/toggle_heart/<string:entity_type>/<int:entity_id>', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_toggle_heart(entity_type, entity_id):
    user_id = session['user_id']
    is_hearted = False
    entity = None

    if entity_type == 'query':
        entity = db.session.get(Query, entity_id)
        if not entity:
            return jsonify({'success': False, 'message': 'Query not found'}), 404
        
        existing_heart = Heart.query.filter_by(user_id=user_id, query_id=entity_id).first()
        if existing_heart:
            db.session.delete(existing_heart)
            is_hearted = False
        else:
            db.session.add(Heart(user_id=user_id, query_id=entity_id))
            is_hearted = True
            
    elif entity_type == 'reply':
        entity = db.session.get(Reply, entity_id)
        if not entity:
            return jsonify({'success': False, 'message': 'Reply not found'}), 404
            
        existing_heart = Heart.query.filter_by(user_id=user_id, reply_id=entity_id).first()
        if existing_heart:
            db.session.delete(existing_heart)
            is_hearted = False
        else:
            db.session.add(Heart(user_id=user_id, reply_id=entity_id))
            is_hearted = True
    
    db.session.commit()

    heart_count = len(entity.hearts) if entity else 0
    
    return jsonify({'success': True, 'is_hearted': is_hearted, 'heart_count': heart_count})

@app.route('/admin/toggle_global_lock', methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_toggle_global_lock():
    lock_setting = Config.query.filter_by(key='is_chat_locked').first()
    if lock_setting:
        is_currently_locked = (lock_setting.value == 'true')
        lock_setting.value = 'false' if is_currently_locked else 'true'
        flash(f"Community Q&A has been globally {'unlocked' if is_currently_locked else 'locked'}.", "success")
    db.session.commit()
    return redirect(url_for('query_solver'))
    
@app.route("/admin/edit_query/<int:query_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_edit_query(query_id):
    user = db.session.get(User, session['user_id'])
    if user.is_forum_blocked:
        blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
        flash(f"You cannot perform this action because you have been blocked by {blocker_name}.", "blocked")
        return redirect(url_for('query_solver'))

    query = db.session.get(Query, query_id)
    if query and query.user_id == session['user_id']:
        new_text = request.form.get("edit_text")
        if new_text and new_text.strip():
            query.text = new_text
            query.edited = True
            db.session.commit()
            flash("Your query has been updated.", "success")
    return redirect(url_for('query_solver'))

@app.route("/admin/edit_reply/<int:reply_id>", methods=["POST"])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_edit_reply(reply_id):
    user = db.session.get(User, session['user_id'])
    if user.is_forum_blocked:
        blocker_name = user.blocker.fullname if user.blocker else "a Super Admin"
        flash(f"You cannot perform this action because you have been blocked by {blocker_name}.", "blocked")
        return redirect(url_for('query_solver'))

    reply = db.session.get(Reply, reply_id)
    if reply and reply.user_id == session['user_id']:
        new_text = request.form.get("edit_text")
        if new_text and new_text.strip():
            reply.text = new_text
            reply.edited = True
            db.session.commit()
            flash("Your reply has been updated.", "success")
    return redirect(url_for('query_solver'))

@app.route("/admin/vote/<string:entity>/<int:id>", methods=['POST'])
@login_required
@role_required("administrator")
@admin_profile_required
def admin_vote(entity, id):
    data = request.get_json()
    vote_type = data.get('vote_type')
    user_id = session['user_id']

    model, vote_model, id_field = (Query, QueryVote, 'query_id') if entity == 'query' else (Reply, ReplyVote, 'reply_id')
    item = db.session.get(model, id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404

    existing_vote = vote_model.query.filter_by(user_id=user_id, **{id_field: id}).first()

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
        else:
            existing_vote.vote_type = vote_type
    else:
        new_vote = vote_model(**{'user_id': user_id, 'vote_type': vote_type, id_field: id})
        db.session.add(new_vote)
    
    db.session.commit()

    total_likes = len([v for v in item.votes if v.vote_type == 'like'])
    total_dislikes = len([v for v in item.votes if v.vote_type == 'dislike'])
    final_vote = vote_model.query.filter_by(user_id=user_id, **{id_field: id}).first()

    return jsonify({
        'success': True, 'likes': total_likes, 'dislikes': total_dislikes,
        'user_vote': final_vote.vote_type if final_vote else None
    })


# ================== STUDENT ROUTES ==================
@app.route("/student/dashboard")
@login_required
@role_required("student")
def student_dashboard():
    user_id = session.get("user_id")
    
    student_info = StudentInfo.query.filter_by(user_id=user_id).first()
    if not student_info:
        flash("Please complete your profile to access all features.", "warning")
        
    user_name = session.get("user_name", "Student")
    return render_template("student_dashboard.html", user_name=user_name)

@app.route("/student/subject_entry", methods=["GET", "POST"])
@login_required
@role_required("student")
@student_profile_required
def subject_entry():
    user_id = session["user_id"]
    student_info = StudentInfo.query.filter_by(user_id=user_id).first()
    branch, sem = student_info.branch, student_info.sem

    # --- MODIFICATION START ---
    # Check if the model can be loaded. This implicitly checks for the CSV file.
    semester_models = load_model(branch, sem)
    if not semester_models:
        # If the CSV/model is not available, render the handler page instead.
        return render_template("student_data_handler.html", branch=branch, sem=sem)
    # --- MODIFICATION END ---

    prev_sem = sem - 1
    prev_subjects = SUBJECTS.get(branch, {}).get(prev_sem, [])
    current_subjects = SUBJECTS.get(branch, {}).get(sem, [])

    current_user = db.session.get(User, user_id)
    is_user_blocked = current_user.is_forum_blocked

    if request.method == "POST":
        _save_marks_from_form(request.form, user_id)
        flash("Marks saved successfully! Your prediction has been updated below.", "success")
        return redirect(url_for('subject_entry'))

    saved_marks = {mark.subject_id: mark.marks for mark in StudentMarks.query.filter_by(user_id=user_id).all()}
    
    predictions, avg_score, level, tips = None, None, None, None

    if semester_models and saved_marks:
        try:
            model_key = f"{branch}_{sem}"
            sample_model = list(MODELS[model_key].values())[0]
            feature_names = sample_model.feature_names_in_

            input_data = {}
            for name in feature_names:
                if name == 'attendance_avg':
                    attendance_values = [v for k, v in saved_marks.items() if k.startswith('prev_attendance_')]
                    input_data[name] = sum(attendance_values) / len(attendance_values) if attendance_values else 0
                elif name == 'attendance_count':
                    input_data[name] = 1 if any(k.startswith('prev_attendance_') for k in saved_marks) else 0
                elif name.endswith('_avg'):
                    sub_id = name[:-4]
                    ct_marks = [v for k, v in saved_marks.items() if k.startswith(f'{sub_id}_ct_')]
                    input_data[name] = sum(ct_marks) / len(ct_marks) if ct_marks else 0
                elif name.endswith('_count'):
                    input_data[name] = 1 if any(k.startswith(f'{sub_id}_ct_') for k in saved_marks) else 0
                else:
                    input_data[name] = saved_marks.get(name, 0)

            input_df = pd.DataFrame([input_data])[feature_names]

            raw_predictions = {
                s['name']: round(max(0, min(70, semester_models[s['id']].predict(input_df)[0])))
                for s in current_subjects
            }
            
            total_predicted_marks = sum(raw_predictions.values())
            predictions = {}
            for subject, mark in raw_predictions.items():
                percentage = (mark / total_predicted_marks) * 100 if total_predicted_marks > 0 else 0
                predictions[subject] = {
                    "mark": mark,
                    "level": categorize_level((mark / 70) * 100),
                    "percentage": round(percentage, 2)
                }

            avg_score = round(sum(raw_predictions.values()) / len(raw_predictions), 2) if raw_predictions else 0
            level = categorize_level((avg_score / 70) * 100)
            tips = "Focus on weaker areas for improvement." if avg_score < 60 else "Keep up the great work!"
        except Exception as e:
            app.logger.error(f"Prediction error for user {user_id}: {e}")
            flash(f"An error occurred during prediction: {e}", "danger")

    
    projected_attendance = {}
    attendance_marks = {k: v for k, v in saved_marks.items() if k.startswith('prev_attendance_')}
    if attendance_marks:
        last_attendance_key = sorted(attendance_marks.keys(), key=lambda k: int(k.split('_')[-1]))[-1]
        last_attendance_value = attendance_marks[last_attendance_key]
        
        last_sem_num = int(last_attendance_key.split('_')[-1])
        projected_attendance[f"Semester {last_sem_num + 1} (Proj.)"] = last_attendance_value

    return render_template("subject_entry.html",
                           student_info=student_info,
                           prev_subjects=prev_subjects,
                           current_subjects=current_subjects,
                           saved_marks=saved_marks,
                           predictions=predictions,
                           avg_score=avg_score,
                           level=level,
                           tips=tips,
                           is_user_blocked=is_user_blocked,
                           error=None,  # Old error message is no longer needed here
                           projected_attendance=projected_attendance
                           )

@app.route("/student/courses")
@login_required
@role_required("student")
@student_profile_required
def my_courses():
    user_id = session.get("user_id")
    student_info = StudentInfo.query.filter_by(user_id=user_id).first()
    courses, notes_by_subject = None, {}

    if student_info and student_info.branch and student_info.sem:
        courses = SUBJECTS.get(student_info.branch, {}).get(student_info.sem)
        if courses:
            for subject in courses:
                notes = StudyMaterial.query.filter_by(subject_id=subject['id']).order_by(StudyMaterial.upload_date.desc()).all()
                notes_by_subject[subject['id']] = notes

    return render_template("my_courses.html", student_info=student_info, courses=courses, notes_by_subject=notes_by_subject)

@app.route("/student/notes/<subject_id>")
@login_required
@role_required("student")
@student_profile_required
def view_notes(subject_id):
    student_info = StudentInfo.query.filter_by(user_id=session['user_id']).first()
    subject_name = ""
    subjects_for_sem = SUBJECTS.get(student_info.branch, {}).get(student_info.sem, [])
    for sub in subjects_for_sem:
        if sub['id'] == subject_id:
            subject_name = sub['name']
            break

    if not subject_name:
        flash("The selected subject is not valid for your current semester.", "danger")
        return redirect(url_for('my_courses'))

    materials = StudyMaterial.query.filter_by(subject_id=subject_id).options(db.joinedload(StudyMaterial.uploader_user)).order_by(StudyMaterial.upload_date.desc()).all()
    return render_template("student_notes.html", materials=materials, subject_name=subject_name)

@app.route('/download/note/<filename>')
@login_required
def download_note(filename):
    return send_from_directory(NOTES_FOLDER, filename, as_attachment=True)
    
@app.route("/student/announcements")
@login_required
@role_required("student")
@student_profile_required
def student_announcements():
    user_id = session['user_id']
    student_info = StudentInfo.query.filter_by(user_id=user_id).first()

    student_branch = student_info.branch
    student_sem = student_info.sem

    announcements = Announcement.query.filter(
        (Announcement.department == 'ALL_BRANCHES') | (Announcement.department == student_branch)
    ).filter(
        (Announcement.semester == None) | (Announcement.semester == 0) | (Announcement.semester == student_sem)
    ).options(db.joinedload(Announcement.user)).order_by(Announcement.timestamp.desc()).all()

    return render_template("student_announcements.html", announcements=announcements)

@app.route('/download_announcement_file/<filename>')
def download_announcement_file(filename):
    return send_from_directory(ANNOUNCEMENTS_FOLDER, filename, as_attachment=True)

# ---------- Query Forum Routes ----------
@app.route("/student/ask_query", methods=["GET", "POST"])
@login_required
@role_required("student")
@student_profile_required
def ask_query():
    user_id = session['user_id']
    current_user = db.session.get(User, user_id)
    chat_lock_status = Config.query.filter_by(key='is_chat_locked').first()
    is_chat_locked = (chat_lock_status.value == 'true') if chat_lock_status else False
    is_user_blocked = current_user.is_forum_blocked

    if request.method == "POST":
        if is_chat_locked or is_user_blocked:
            flash("You are currently unable to post in the forum.", "warning")
            return redirect(url_for('ask_query'))
        query_text = request.form.get("query_text")
        if query_text and query_text.strip():
            db.session.add(Query(text=query_text, user_id=user_id))
            db.session.commit()
            flash("Your query has been posted successfully!", "success")
        return redirect(url_for('ask_query'))

    queries_query = db.session.query(Query).options(
        subqueryload(Query.replies).subqueryload(Reply.hearts).joinedload(Heart.author),
        subqueryload(Query.replies).joinedload(Reply.author).joinedload(User.admin_info),
        subqueryload(Query.replies).joinedload(Reply.author).joinedload(User.student_info),
        subqueryload(Query.hearts).joinedload(Heart.author),
        joinedload(Query.author).joinedload(User.admin_info),
        joinedload(Query.author).joinedload(User.student_info)
    ).order_by(desc(Query.is_pinned), desc(Query.timestamp)).all()

    for query in queries_query:
        query.user_vote = QueryVote.query.filter_by(user_id=user_id, query_id=query.id).first()
        query.hearted_by_admins = [heart.author.fullname for heart in query.hearts if heart.author.role == 'administrator']
        for reply in query.replies:
            reply.user_vote = ReplyVote.query.filter_by(user_id=user_id, reply_id=reply.id).first()
            reply.hearted_by_admins = [heart.author.fullname for heart in reply.hearts if heart.author.role == 'administrator']

    return render_template("student_ask.html", queries=queries_query, is_chat_locked=is_chat_locked, is_user_blocked=is_user_blocked, **{'current_user': current_user})

@app.route("/student/post_reply/<int:query_id>", methods=["POST"])
@login_required
@student_profile_required
def post_reply(query_id):
    chat_lock_status = Config.query.filter_by(key='is_chat_locked').first()
    is_chat_locked = (chat_lock_status.value == 'true') if chat_lock_status else False
    user = db.session.get(User, session['user_id'])

    if is_chat_locked or user.is_forum_blocked:
        flash("You are currently unable to post replies.", "warning")
        return redirect(url_for('ask_query'))
        
    reply_text = request.form.get("reply_text")
    parent_id = request.form.get("parent_id")
    
    if reply_text and reply_text.strip() and Query.query.get(query_id):
        new_reply = Reply(
            text=reply_text, 
            user_id=session['user_id'], 
            query_id=query_id,
            parent_id=int(parent_id) if parent_id and parent_id.isdigit() else None
        )
        db.session.add(new_reply)
        db.session.commit()
        flash("Your reply has been posted.", "success")
        return redirect(url_for('ask_query', _anchor=f'reply-{new_reply.id}'))
    return redirect(url_for('ask_query'))

@app.route("/student/edit_query/<int:query_id>", methods=["POST"])
@login_required
@student_profile_required
def edit_query(query_id):
    query = db.session.get(Query, query_id)
    if query and query.user_id == session['user_id']:
        new_text = request.form.get("edit_text")
        if new_text and new_text.strip():
            query.text = new_text
            query.edited = True
            db.session.commit()
            flash("Your query has been updated.", "success")
        else:
            flash("Edit cannot be empty.", "warning")
    else:
        flash("You are not authorized to edit this query.", "danger")
    return redirect(url_for('ask_query', _anchor=f'query-{query_id}'))

@app.route("/student/edit_reply/<int:reply_id>", methods=["POST"])
@login_required
@student_profile_required
def edit_reply(reply_id):
    reply = db.session.get(Reply, reply_id)
    if reply and reply.user_id == session['user_id']:
        new_text = request.form.get("edit_text")
        if new_text and new_text.strip():
            reply.text = new_text
            reply.edited = True
            db.session.commit()
            flash("Your reply has been updated.", "success")
        else:
            flash("Edit cannot be empty.", "warning")
    else:
        flash("You are not authorized to edit this reply.", "danger")
    return redirect(url_for('ask_query'))

@app.route("/student/delete_query/<int:query_id>", methods=["POST"])
@login_required
@student_profile_required
def delete_query(query_id):
    query = db.session.get(Query, query_id)
    if query and query.user_id == session['user_id']:
        db.session.delete(query)
        db.session.commit()
        flash("Your query has been deleted.", "success")
    else:
        flash("You are not authorized to delete this query.", "danger")
    return redirect(url_for('ask_query'))

@app.route("/student/delete_reply/<int:reply_id>", methods=["POST"])
@login_required
@student_profile_required
def delete_reply(reply_id):
    reply = db.session.get(Reply, reply_id)
    if reply and reply.user_id == session['user_id']:
        db.session.delete(reply)
        db.session.commit()
        flash("Your reply has been deleted.", "success")
    else:
        flash("You are not authorized to delete this reply.", "danger")
    return redirect(url_for('ask_query'))

@app.route('/student/vote/<string:entity>/<int:id>', methods=['POST'])
@login_required
@student_profile_required
def vote(entity, id):
    data = request.get_json()
    vote_type = data.get('vote_type')
    user_id = session['user_id']

    if vote_type not in ['like', 'dislike']:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    model, vote_model, id_field = (Query, QueryVote, 'query_id') if entity == 'query' else (Reply, ReplyVote, 'reply_id')
    item = db.session.get(model, id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404

    existing_vote = vote_model.query.filter_by(user_id=user_id, **{id_field: id}).first()

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
        else:
            existing_vote.vote_type = vote_type
    else:
        new_vote = vote_model(**{'user_id': user_id, 'vote_type': vote_type, id_field: id})
        db.session.add(new_vote)
    
    db.session.commit()

    total_likes = len([v for v in item.votes if v.vote_type == 'like'])
    total_dislikes = len([v for v in item.votes if v.vote_type == 'dislike'])
    
    final_vote = vote_model.query.filter_by(user_id=user_id, **{id_field: id}).first()

    return jsonify({
        'success': True, 'likes': total_likes, 'dislikes': total_dislikes,
        'user_vote': final_vote.vote_type if final_vote else None
    })

@app.route('/blog')
def blog():
    """Renders the blog page."""
    return render_template('blog.html')

@app.route('/privacy')
def privacy():
    """Renders the privacy policy page."""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """Renders the terms of service page."""
    return render_template('terms.html')

@app.route('/faq')
def faq():
    """Renders the FAQ page."""
    return render_template('faq.html')


if __name__ == "__main__":
    app.run(debug=True)
