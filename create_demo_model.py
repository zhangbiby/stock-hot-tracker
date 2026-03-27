#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速创建演示用ML模型
用于在没有足够历史数据时启用ML功能演示
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

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

def create_demo_model():
    """创建一个简单的演示模型"""
    try:
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        import numpy as np
        
        print("=" * 50)
        print("Creating Demo ML Model...")
        print("=" * 50)
        
        # 创建简单的演示模型（基于常见模式）
        # 使用随机数据训练一个基础模型
        np.random.seed(42)
        
        # 生成一些演示数据
        n_samples = 200
        X = np.random.randn(n_samples, 10)
        # 模拟：排名好 + 涨幅适中 = 上涨概率高
        y = ((X[:, 0] < 30) & (X[:, 1] > 0) & (X[:, 1] < 5)).astype(int)
        
        # 训练简单模型
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=3,
            random_state=42
        )
        model.fit(X_scaled, y)
        
        # 保存模型
        feature_cols = [
            'rank', 'change_pct', 'turnover_rate', 'volume_ratio',
            'amplitude', 'rsi', 'macd', 'bb_position', 'ma5_diff', 'ma20_diff'
        ]
        
        model_data = {
            'model': model,
            'scaler': scaler,
            'feature_cols': feature_cols,
            'accuracy': 0.65,  # 演示用准确率
            'train_size': n_samples,
            'train_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'demo': True  # 标记为演示模型
        }
        
        model_file = OUTPUT_DIR / "stock_model.pkl"
        joblib.dump(model_data, model_file)
        
        # 保存元数据
        meta = {
            'train_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'samples': n_samples,
            'accuracy': 0.65,
            'feature_cols': feature_cols,
            'model_type': 'RandomForestClassifier (Demo)',
            'note': 'This is a demo model for testing purposes'
        }
        with open(OUTPUT_DIR / "model_meta.json", 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Demo model created: {model_file}")
        print(f"   Accuracy: 65% (demo)")
        print(f"   Features: {', '.join(feature_cols)}")
        print("\nNote: This is a demo model. For production use,")
        print("      run build_training_data.py to collect real data.")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Install: pip install scikit-learn joblib numpy")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = create_demo_model()
    sys.exit(0 if success else 1)
