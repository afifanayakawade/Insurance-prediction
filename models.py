from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    predictions = db.relationship(
        "Prediction",
        backref="user",
        lazy=True
    )

class Prediction(db.Model):

    __tablename__ = "predictions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    age = db.Column(db.Integer)

    sex = db.Column(
        db.String(20)
    )

    bmi = db.Column(
        db.Float
    )

    dependents = db.Column(
        db.Integer
    )

    smoker = db.Column(
        db.String(10)
    )

    salary = db.Column(
        db.Float
    )

    expenditure = db.Column(
        db.Float
    )

    occupation = db.Column(
        db.String(50)
    )

    chronic_diseases = db.Column(
        db.String(100)
    )

    alcoholic = db.Column(
        db.String(10)
    )

    marital_status = db.Column(
        db.String(10)
    )

    predicted_charges = db.Column(
        db.Float
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )