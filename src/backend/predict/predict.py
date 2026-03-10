# coding:utf-8

import streamlit as st
import torch
import joblib

from transformers import(
    AutoTokenizer,
    AutoModelForSequenceClassification
)


# Load AI model
path_trainer_predict = st.session_state.get("trainer_path_model")

model = AutoModelForSequenceClassification.from_pretrained(path_trainer_predict)
tokenizer = AutoTokenizer.from_pretrained(path_trainer_predict)

# Load LabelEncoder
label_encoder = joblib.load(path_trainer_predict + "\label_encoder.pkl")


# =========== Predidt =========
def predict(row):
    
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    text = f"{row['Minesite']} | {row['Labour Type']} | {row['Comments']}"
    inputs = tokenizer(
        text,
        return_tensors= "pt",
        truncation= True,
        padding= True,
        max_length= 256
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    prediction = torch.argmax(outputs.logits, dim= 1).item()

    return label_encoder.inverse_transform([prediction])[0]