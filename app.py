
from flask import Flask, render_template, request
import joblib
import pandas as pd

app = Flask(__name__)

# Load ML model & encoder
model = joblib.load("should_i_bunk_model.pkl")
label_encoder = joblib.load("label_encoder.pkl")

# ML feature list (attendance_percent will be auto-inserted)
feature_columns = [
    "attendance_percent",
    "subject_difficulty",
    "class_importance",
    "upcoming_exam",
    "assignment_due",
    "sleep_hours",
    "stress_level",
    "mood",
    "health_condition",
    "teacher_strictness",
    "class_engagement",
    "weather",
    "day_of_week"
]

# Human-friendly messages
prediction_messages = {
    "Yes": "YES – You can bunk today.",
    "No": "NO – You should attend the class today."
}


def generate_reasoning(data_dict):
    reasons = []

    if data_dict["attendance_percent"] < 70:
        reasons.append("Your attendance is low.")
    if data_dict["sleep_hours"] < 5:
        reasons.append("You slept very little.")
    if data_dict["stress_level"] > 7:
        reasons.append("Your stress level is high.")
    if data_dict["class_importance"] >= 4:
        reasons.append("Today's class is important.")
    if data_dict["teacher_strictness"] >= 4:
        reasons.append("Teacher is very strict.")
    if data_dict["class_engagement"] <= 2:
        reasons.append("The class is usually boring.")
    if data_dict["health_condition"] <= 2:
        reasons.append("Your health condition is weak.")

    return " | ".join(reasons) if reasons else "No major influencing factors found."


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/predict', methods=['POST'])
def predict():
    if "reset" in request.form:
        return render_template("index.html")

    try:
        # -------------------------
        # 1. Attendance Forecasting Inputs
        # -------------------------
        present_attendance = float(request.form["present_attendance"])
        classes_conducted = float(request.form["classes_conducted"])
        total_classes = float(request.form["total_classes"])

        # Calculate attended classes
        attended = (present_attendance / 100) * classes_conducted

        # Attendance if attending today
        attendance_if_attend = (attended + 1) / (classes_conducted + 1) * 100

        # Attendance if bunking today
        attendance_if_bunk = attended / (classes_conducted + 1) * 100

        attendance_if_attend = round(attendance_if_attend, 2)
        attendance_if_bunk = round(attendance_if_bunk, 2)

        # -------------------------
        # 2. ML Prediction Inputs
        # -------------------------
        data_dict = {}

        # Auto-use present attendance for ML feature
        data_dict["attendance_percent"] = present_attendance

        # Loop for other ML inputs
        for col in feature_columns:
            if col == "attendance_percent":
                continue
            data_dict[col] = float(request.form[col])

        # Convert dict → DataFrame
        df = pd.DataFrame([data_dict.values()], columns=feature_columns)

        # ML Prediction
        pred = model.predict(df)[0]
        final_label = label_encoder.inverse_transform([pred])[0]

        # Probability
        prob = round(model.predict_proba(df)[0][pred] * 100, 2)

        # Generate reasoning
        reasoning = generate_reasoning(data_dict)

        # -------------------------
        # 3. Combined Final Decision
        # -------------------------
        if attendance_if_bunk < 75:
            final_message = "NO – You cannot bunk today. Attendance will fall below 75%."
        else:
            final_message = prediction_messages[final_label]

        return render_template(
            "index.html",
            prediction_text=f"Prediction: {final_message}",
            probability_text=f"Probability: {prob}%",
            reasoning_text=f"Reason: {reasoning}",
            attendance_bunk=f"Attendance if you bunk today: {attendance_if_bunk}%",
            attendance_attend=f"Attendance if you attend today: {attendance_if_attend}%"
        )

    except Exception as e:
        return f"Error occurred: {e}"


if __name__ == "__main__":
    app.run(debug=True)
