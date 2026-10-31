from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, User, Prediction
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

import os
import joblib
import numpy as np
import pandas as pd

app = Flask(__name__)

import os

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:YOUR_PASSWORD@localhost:5432/insurance_db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "model",
    "insurance_model_pipeline.joblib"
)

saved_model = joblib.load(MODEL_PATH)

pipeline = saved_model["pipeline"]

numeric_cols = saved_model["numeric_cols"]

categorical_cols = saved_model["categorical_cols"]

target_col = saved_model["target_col"]

apply_log = saved_model["apply_log"]


if isinstance(saved_model, dict):

    pipeline = saved_model.get("pipeline")

    apply_log = saved_model.get(
        "apply_log",
        False
    )

else:

    pipeline = saved_model

    apply_log = False

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


def add_engineered_features(df):

    df = df.copy()

    # BMI squared
    df["bmi_sq"] = df["bmi"] ** 2

    # Smoker flag
    df["smoker_flag"] = df["smoker"].apply(
        lambda x: 1 if str(x).lower() == "yes" else 0
    )

    # Age × smoker
    df["age_x_smoker"] = (
        df["age"] * df["smoker_flag"]
    )

    # Expenditure / Salary ratio
    df["spend_ratio"] = (
        df["expenditure"] /
        (df["salary"] + 1)
    )

    # Chronic disease count
    def chronic_count_val(x):

        s = str(x).strip().lower()

        if s in ["none", "", "nan", "no"]:
            return 0

        return len([
            d for d in s.split(",")
            if d.strip() != ""
        ])

    df["chronic_count"] = (
        df["chronic_diseases"]
        .apply(chronic_count_val)
    )

    return df

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/about")
def about():
    return render_template("about.html")

# Signup page
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("signup"))

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered.")
            return redirect(url_for("signup"))

        # Hash password
        hashed_password = generate_password_hash(password)

        # Create user
        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            return redirect(url_for("dashboard"))

        else:

            flash("Invalid email or password.")

            return redirect(url_for("login"))

    return render_template("login.html")

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        user=current_user
    )

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():

    prediction = None

    if request.method == "POST":

        try:

            # -------------------------
            # Get form values
            # -------------------------

            age = float(request.form["age"])

            sex = request.form["sex"].lower()

            bmi = float(request.form["bmi"])

            dependents = float(
                request.form["dependents"]
            )

            smoker = request.form["smoker"].lower()

            salary = float(
                request.form["salary"]
            )

            expenditure = float(
                request.form["expenditure"]
            )

            occupation = request.form["occupation"]

            chronic_diseases = request.form["chronic_diseases"]

            alcoholic = request.form["alcoholic"]

            marital_status = request.form["marital_status"]


            # # -------------------------
            # # Chronic disease handling
            # # -------------------------

            # if chronic_diseases.strip() in ["", "none"]:

            #     chronic_diseases = "no"


            # -------------------------
            # Create DataFrame
            # -------------------------

            user_data = pd.DataFrame({

                "age": [age],

                "sex": [sex],

                "bmi": [bmi],

                "dependents": [dependents],

                "smoker": [smoker],

                "salary": [salary],

                "expenditure": [expenditure],

                "occupation": [occupation],

                "chronic_diseases": [
                    chronic_diseases
                ],

                "alcoholic": [alcoholic],

                "marital_status": [
                    marital_status
                ]

            })


            # -------------------------
            # Feature Engineering
            # -------------------------

            engineered_input = (
                add_engineered_features(
                    user_data
                )
            )


            # -------------------------
            # Prediction
            # -------------------------

            prediction = pipeline.predict(
                engineered_input
            )[0]


            # -------------------------
            # Reverse log transformation
            # -------------------------

            if apply_log:

                prediction = np.expm1(
                    prediction
                )


            prediction = float(prediction)

            # -------------------------
            # Save prediction to PostgreSQL
            # -------------------------

            new_prediction = Prediction(

                user_id=current_user.id,

                age=int(age),

                sex=sex,

                bmi=float(bmi),

                dependents=int(dependents),

                smoker=smoker,

                salary=float(salary),

                expenditure=float(expenditure),

                occupation=occupation,

                chronic_diseases=chronic_diseases,

                alcoholic=alcoholic,

                marital_status=marital_status,

                predicted_charges=prediction
            )

            db.session.add(new_prediction)

            db.session.commit()


        except Exception as e:

            flash(
                f"Prediction failed: {str(e)}"
            )

            return redirect(
                url_for("predict")
            )


    return render_template(
        "prediction.html",
        prediction=prediction
    )

@app.route("/history")
@login_required
def history():

    predictions = Prediction.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Prediction.created_at.desc()
    ).all()

    return render_template(
        "history.html",
        predictions=predictions
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
