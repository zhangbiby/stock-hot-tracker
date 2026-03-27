#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习模型训练脚本
使用随机森林分类器预测股票短期涨跌
输出: output/stock_model.pkl
"""

import sys
import json
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    except:
        pass

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# 特征列（与 build_training_data.py 保持一致）
FEATURE_COLS = [
    'rank', 'change_pct', 'turnover_rate', 'volume_ratio',
    'amplitude', 'rsi', 'macd', 'bb_position', 'ma5_diff', 'ma20_diff'
]
TARGET_COL = 'target'
MIN_SAMPLES = 50   # 最少样本数才训练


def check_dependencies():
    """检查依赖是否安装"""
    missing = []
    for pkg in ['sklearn', 'pandas', 'joblib']:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Missing packages: {missing}")
        print("Install: pip install scikit-learn pandas joblib")
        return False
    return True


def train():
    """训练模型"""
    print("=" * 50)
    print("Training ML model...")
    print("=" * 50)
    
    if not check_dependencies():
        return False
    
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report
    import joblib
    
    # 加载训练数据
    data_file = OUTPUT_DIR / "training_data.csv"
    if not data_file.exists():
        print("training_data.csv not found. Run: python build_training_data.py")
        return False
    
    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} samples")
    
    if len(df) < MIN_SAMPLES:
        print(f"Too few samples ({len(df)} < {MIN_SAMPLES}). Need more data.")
        print("Keep running the collector to accumulate data.")
        return False
    
    # 准备特征
    X = df[FEATURE_COLS].copy()
    y = df[TARGET_COL].copy()
    
    # 填充缺失值（用列均值）
    X = X.fillna(X.mean())
    
    print(f"Features: {FEATURE_COLS}")
    print(f"Samples: {len(X)}, Up: {y.sum()}, Down: {(y==0).sum()}")
    
    # 划分训练/测试集（按时间顺序，不随机）
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    
    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)
    
    # 训练随机森林
    print("\nTraining RandomForest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_leaf=5,
        random_state=42,
        class_weight='balanced'
    )
    rf.fit(X_train_scaled, y_train)
    
    # 评估
    y_pred = rf.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Down', 'Up']))
    
    # 特征重要性
    print("\nFeature Importance:")
    importances = sorted(zip(FEATURE_COLS, rf.feature_importances_), key=lambda x: -x[1])
    for feat, imp in importances:
        bar = "█" * int(imp * 50)
        print(f"  {feat:<15} {imp:.4f} {bar}")
    
    # 如果样本足够多，也训练逻辑回归作为对比
    lr_acc = None
    if len(X_train) >= 100:
        print("\nTraining LogisticRegression (comparison)...")
        lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
        lr.fit(X_train_scaled, y_train)
        lr_pred = lr.predict(X_test_scaled)
        lr_acc = accuracy_score(y_test, lr_pred)
        print(f"LogisticRegression Accuracy: {lr_acc:.4f}")
    
    # 选择最佳模型
    best_model = rf
    best_acc   = acc
    
    # 保存模型
    model_data = {
        'model':        best_model,
        'scaler':       scaler,
        'feature_cols': FEATURE_COLS,
        'accuracy':     best_acc,
        'train_size':   len(X_train),
        'train_time':   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    model_file = OUTPUT_DIR / "stock_model.pkl"
    joblib.dump(model_data, model_file)
    print(f"\nModel saved to: {model_file}")
    
    # 保存训练元数据
    meta = {
        'train_time':   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'samples':      len(df),
        'train_size':   len(X_train),
        'test_size':    len(X_test),
        'accuracy':     round(best_acc, 4),
        'feature_cols': FEATURE_COLS,
        'model_type':   'RandomForestClassifier',
    }
    with open(OUTPUT_DIR / "model_meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    print("\nTraining complete!")
    return True


if __name__ == "__main__":
    success = train()
    if not success:
        sys.exit(1)
