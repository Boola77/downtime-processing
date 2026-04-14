# coding:utf-8

import os
import streamlit as st
import torch
import joblib

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)


# =====================================================
# LOAD MODEL (cached ⚡)
# =====================================================
@st.cache_resource
def load_model_and_tokenizer(path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = AutoModelForSequenceClassification.from_pretrained(path)
    tokenizer = AutoTokenizer.from_pretrained(path)

    model.to(device)
    model.eval()

    return model, tokenizer, device


@st.cache_resource
def load_label_encoder(path):
    return joblib.load(path)


# ---- paths ----
path_trainer_predict = st.session_state.get("trainer_path_model")
label_path = os.path.join(path_trainer_predict, "label_encoder.pkl")

# ---- load once ----
model, tokenizer, device = load_model_and_tokenizer(path_trainer_predict)
label_encoder = load_label_encoder(label_path)


# =====================================================
# 🚀 BATCH PREDICT (FAST)
# =====================================================
def predict_batch(df, batch_size=64):
    """
    Predict Description CAT for a dataframe (vectorized ⚡)
    """

    results = []

    # ---- loop by batch ----
    for i in range(0, len(df), batch_size):
        chunk = df.iloc[i:i+batch_size]

        texts = (
            chunk['Minesite'].astype(str) + " | " +
            chunk['Labour Type'].astype(str) + " | " +
            chunk['Comments'].astype(str)
        ).tolist()

        inputs = tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()

        decoded = label_encoder.inverse_transform(preds)
        results.extend(decoded)

    return results


# =====================================================
# SAFE FILL FUNCTION (used in your app)
# =====================================================
def fill_description_cat(df):
    df = df.copy()

    if 'Description CAT' not in df.columns:
        return df

    mask = df['Description CAT'].isna()

    if mask.any():
        df.loc[mask, 'Description CAT'] = predict_batch(df.loc[mask])

    return df