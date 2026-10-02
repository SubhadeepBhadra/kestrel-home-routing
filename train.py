"""
Kestrel Home Service Routing - Training & Validation Pipeline
Trains a calibrated multi-class classifier on historical service resolution logs.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import re
from sklearn.model_selection import StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

CANONICAL_MAP = {
    'Installs & Demo': 'Installations',
    'Installations': 'Installations',
    'Filters & Consumables': 'Consumables',
    'Consumables': 'Consumables',
    'Repairs': 'Repairs',
    'Billing': 'Billing',
    'Returns & Replacement': 'Returns & Replacement',
    'Warranty Claims': 'Warranty Claims',
    'Product Advice': 'Product Advice'
}

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace('â€¦', '...').replace('â€™', "'").replace('â€œ', '"').replace('â€', '"').replace('hélp', 'help')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_pipeline():
    preprocessor = ColumnTransformer(
        transformers=[
            ('text_word', TfidfVectorizer(ngram_range=(1, 3), min_df=2, max_features=25000, sublinear_tf=True), 'clean_text'),
            ('text_char', TfidfVectorizer(ngram_range=(3, 5), analyzer='char_wb', min_df=3, max_features=35000, sublinear_tf=True), 'clean_text'),
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['channel', 'product_family', 'warranty_status'])
        ]
    )
    clf = CalibratedClassifierCV(LinearSVC(C=1.0, dual=False, max_iter=2000, random_state=42), cv=3)
    return Pipeline([('prep', preprocessor), ('clf', clf)])

def train_and_evaluate(data_dir: str, output_model: str, output_pred: str):
    train_path = os.path.join(data_dir, "train.csv")
    res_path = os.path.join(data_dir, "resolution_log.csv")
    test_path = os.path.join(data_dir, "test_unlabelled.csv")

    if not os.path.exists(train_path) or not os.path.exists(res_path):
        print(f"Error: Required datasets not found in {data_dir}")
        sys.exit(1)

    train_df = pd.read_csv(train_path)
    res_df = pd.read_csv(res_path)
    merged = pd.merge(train_df, res_df, on="request_id")

    # Map to canonical 7 departments
    merged['target'] = merged['final_team'].map(CANONICAL_MAP)
    merged['clean_text'] = merged['request_text'].apply(clean_text)

    print(f"Loaded {len(merged)} training samples across 7 queues.")

    # 5-Fold Stratified Cross Validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pipeline = build_pipeline()

    oof_preds = [None] * len(merged)
    for fold, (tr_idx, val_idx) in enumerate(skf.split(merged, merged['target'])):
        X_tr, y_tr = merged.iloc[tr_idx][['clean_text', 'channel', 'product_family', 'warranty_status']], merged.iloc[tr_idx]['target']
        X_va, y_va = merged.iloc[val_idx][['clean_text', 'channel', 'product_family', 'warranty_status']], merged.iloc[val_idx]['target']

        pipeline.fit(X_tr, y_tr)
        preds = pipeline.predict(X_va)
        for idx, pred in zip(val_idx, preds):
            oof_preds[idx] = pred

    acc = accuracy_score(merged['target'], oof_preds)
    print(f"\n--- 5-Fold Stratified Cross-Validation Accuracy: {acc*100:.2f}% ---")
    print("\nClassification Report:")
    print(classification_report(merged['target'], oof_preds, digits=4))

    # Fit on all training data
    print("\nFitting final model on full dataset...")
    pipeline.fit(merged[['clean_text', 'channel', 'product_family', 'warranty_status']], merged['target'])
    joblib.dump(pipeline, output_model)
    print(f"Saved trained model to {output_model}")

    # Predict test if file present
    if os.path.exists(test_path):
        test_df = pd.read_csv(test_path)
        test_df['clean_text'] = test_df['request_text'].apply(clean_text)
        test_preds = pipeline.predict(test_df[['clean_text', 'channel', 'product_family', 'warranty_status']])
        
        sub = pd.DataFrame({
            'request_id': test_df['request_id'],
            'team': test_preds
        })
        sub.to_csv(output_pred, index=False)
        print(f"Saved test predictions ({len(sub)} rows) to {output_pred}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Kestrel Service Request Classifier")
    parser.add_argument("--data_dir", type=str, default="data", help="Directory containing train.csv, resolution_log.csv, test_unlabelled.csv")
    parser.add_argument("--model_out", type=str, default="model.joblib", help="Output path for trained model artifact")
    parser.add_argument("--pred_out", type=str, default="predictions.csv", help="Output path for test predictions")
    args = parser.parse_args()

    train_and_evaluate(args.data_dir, args.model_out, args.pred_out)
