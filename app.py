import streamlit as st
import pandas as pd
import pickle
import numpy as np
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import time

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",  # Replace with your MySQL username
    "password": "Ytmp3.eu",  # Replace with your MySQL password
    "database": "student_performance"
}

# Initialize MySQL connection with reconnect logic
def get_connection(max_retries=3):
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                return connection
        except Error as e:
            if attempt == max_retries - 1:
                st.error(f"❌ Database connection failed after {max_retries} attempts: {e}")
                return None
            time.sleep(1)  # Wait before retrying
    return None

# Create table if not exists (with connection handling)
def create_table(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME,
            age INT,
            year_of_study INT,
            attendance INT,
            assignment_score INT,
            midterm_score INT,
            final_score INT,
            tuition_paid INT,
            outstanding_balance INT,
            books_borrowed INT,
            library_visits INT,
            days_absent INT,
            gender_male BOOLEAN,
            department_cs BOOLEAN,
            department_ee BOOLEAN,
            parents_primary BOOLEAN,
            parents_university BOOLEAN,
            chronic_illness BOOLEAN,
            prediction VARCHAR(20),
            confidence FLOAT
        )
        """)
        connection.commit()
        cursor.close()
    except Error as e:
        st.error(f"Error creating table: {e}")

# Function to maintain connection
def maintain_connection():
    if not st.session_state.get('db_connected') or not st.session_state.connection.is_connected():
        st.session_state.connection = get_connection()
        if st.session_state.connection and st.session_state.connection.is_connected():
            st.session_state.db_connected = True
            create_table(st.session_state.connection)
        else:
            st.session_state.db_connected = False

# Load the model
@st.cache_resource
def load_model():
    with open('random_forest_model.pkl', 'rb') as file:
        model = pickle.load(file)
    return model

model = load_model()

# Dashboard title
st.title("🎓 Student Performance Prediction Dashboard")
st.markdown("""
This app predicts student performance and saves results to MySQL database.
""")

# Initialize session state for database status
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
    st.session_state.connection = None

# Sidebar for user input and database controls
with st.sidebar:
    st.header('📝 Input Student Parameters')
    
    # Database connection button
    if st.button('🔌 Connect to Database'):
        maintain_connection()
        if st.session_state.db_connected:
            st.success("✅ Successfully connected to database!")
        else:
            st.error("❌ Failed to connect to database")

    # Connection status indicator
    if st.session_state.get('db_connected'):
        st.success("Database: Connected")
    else:
        st.error("Database: Not Connected")

    st.markdown("---")
    
    # Input fields
    st.subheader("Academic Metrics")
    age = st.slider('Age', 15, 30, 20)
    year_of_study = st.slider('Year of Study', 1, 5, 2)
    attendance = st.slider('Attendance (%)', 0, 100, 75)
    assignment_score = st.slider('Assignment Score', 0, 100, 70)
    midterm_score = st.slider('Midterm Score', 0, 100, 65)
    final_score = st.slider('Final Score', 0, 100, 60)
    
    st.subheader("Financial Information")
    tuition_paid = st.slider('Tuition Paid (%)', 0, 100, 80)
    outstanding_balance = st.slider('Outstanding Balance ($)', 0, 10000, 2000)
    
    st.subheader("Library Activity")
    books_borrowed = st.slider('Books Borrowed', 0, 50, 5)
    library_visits = st.slider('Library Visits (per semester)', 0, 100, 10)
    days_absent = st.slider('Days Absent', 0, 100, 5)
    
    st.subheader("Demographic Information")
    gender = st.radio('Gender', ['Female', 'Male'])
    department = st.selectbox('Department', 
                            ['Other', 'Computer Science', 'Electrical Engineering'])
    parents_education = st.selectbox("Parents' Education Level", 
                                   ['Other', 'Primary', 'University'])
    chronic_illness = st.radio('Chronic Illness', ['No', 'Yes'])

# Prepare input data
input_data = {
    'Age': age,
    'Year_of_Study': year_of_study,
    'Attendance': attendance,
    'Assignment_Score': assignment_score,
    'Midterm_Score': midterm_score,
    'Final_Score': final_score,
    'Tuition_Paid': tuition_paid,
    'Outstanding_Balance': outstanding_balance,
    'Books_Borrowed': books_borrowed,
    'Library_Visits': library_visits,
    'Days_Absent': days_absent,
    'Gender_Male': 1 if gender == 'Male' else 0,
    'Department_Computer Science': 1 if department == 'Computer Science' else 0,
    'Department_Electrical Engineering': 1 if department == 'Electrical Engineering' else 0,
    'Parents_Education_Primary': 1 if parents_education == 'Primary' else 0,
    'Parents_Education_University': 1 if parents_education == 'University' else 0,
    'Chronic_Illness_Yes': 1 if chronic_illness == 'Yes' else 0
}

input_df = pd.DataFrame(input_data, index=[0])

# Main panel
st.subheader('📋 User Input Summary')
st.write(input_df)

# Prediction and save to database
if st.button('🚀 Predict & Save to Database'):
    maintain_connection()  # Ensure connection exists before prediction
    
    if not st.session_state.db_connected:
        st.error("Database connection failed. Please check:")
        st.error("- Is MySQL server running?")
        st.error("- Are the credentials correct in DB_CONFIG?")
        st.error("- Try connecting manually with these credentials")
    else:
        try:
            # Make prediction
            prediction = model.predict(input_df)
            prediction_proba = model.predict_proba(input_df)
            
            performance_classes = ['Low Performance', 'High Performance']
            predicted_class = performance_classes[prediction[0]]
            confidence = max(prediction_proba[0])
            
            # Save to database
            cursor = st.session_state.connection.cursor()
            query = """
            INSERT INTO predictions (
                timestamp, age, year_of_study, attendance, assignment_score,
                midterm_score, final_score, tuition_paid, outstanding_balance,
                books_borrowed, library_visits, days_absent, gender_male,
                department_cs, department_ee, parents_primary, parents_university,
                chronic_illness, prediction, confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                datetime.now(),
                input_data['Age'],
                input_data['Year_of_Study'],
                input_data['Attendance'],
                input_data['Assignment_Score'],
                input_data['Midterm_Score'],
                input_data['Final_Score'],
                input_data['Tuition_Paid'],
                input_data['Outstanding_Balance'],
                input_data['Books_Borrowed'],
                input_data['Library_Visits'],
                input_data['Days_Absent'],
                input_data['Gender_Male'],
                input_data['Department_Computer Science'],
                input_data['Department_Electrical Engineering'],
                input_data['Parents_Education_Primary'],
                input_data['Parents_Education_University'],
                input_data['Chronic_Illness_Yes'],
                predicted_class,
                confidence
            )
            
            cursor.execute(query, values)
            st.session_state.connection.commit()
            cursor.close()
            
            # Display results
            st.success("✅ Prediction saved to database!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader('🎯 Prediction')
                if prediction[0] == 1:
                    st.success(f"✅ {predicted_class}")
                else:
                    st.error(f"⚠️ {predicted_class}")
            
            with col2:
                st.subheader('📈 Confidence')
                prob_df = pd.DataFrame({
                    'Performance': performance_classes,
                    'Probability': prediction_proba[0]
                }).set_index('Performance')
                st.write(prob_df)
                st.bar_chart(prob_df)
            
            # Show recent predictions
            st.subheader("📊 Recent Predictions")
            cursor = st.session_state.connection.cursor()
            cursor.execute("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 5")
            recent_data = cursor.fetchall()
            
            if recent_data:
                columns = [i[0] for i in cursor.description]
                recent_df = pd.DataFrame(recent_data, columns=columns)
                st.dataframe(recent_df[['timestamp', 'age', 'prediction', 'confidence']])
            else:
                st.info("No predictions in database yet")
            cursor.close()
                
        except Error as e:
            st.error(f"Database error: {e}")
            st.session_state.db_connected = False

# Database management section
st.markdown("---")
st.subheader("🔧 Database Management")

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Check Connection Status"):
        maintain_connection()
        if st.session_state.db_connected:
            st.success("Database connection is active!")
        else:
            st.error("Database connection is not active")

with col2:
    if st.button("🧹 Clear All Predictions"):
        if st.session_state.get('db_connected'):
            try:
                cursor = st.session_state.connection.cursor()
                cursor.execute("TRUNCATE TABLE predictions")
                st.session_state.connection.commit()
                cursor.close()
                st.success("All predictions cleared from database!")
            except Error as e:
                st.error(f"Error clearing database: {e}")
        else:
            st.error("No active database connection")

# Add some style
st.markdown("""
<style>
    .stButton>button {
        border-radius: 0.5em;
        font-size: 1.1em;
        margin: 0.5em 0;
    }
    .st-bb {
        background-color: #4CAF50;
        color: white;
    }
    .st-bb:hover {
        background-color: #45a049;
    }
    .st-c0 {
        background-color: #f0f2f6;
    }
    .css-1aumxhk {
        background-color: #ffffff;
    }
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)