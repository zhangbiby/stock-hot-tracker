# -*- coding: utf-8 -*-
"""
MLSC Trainer
MLSC多标签股票分类器训练器
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from datetime import datetime
import json

from .mlsc_model import CNNAttentionGRU, MLSCConfig


class StockSequenceDataset(Dataset):
    """
    股票序列数据集
    
    数据格式:
    X: (N, seq_len, input_dim) - N个样本，seq_len天序列，input_dim个特征
    y: (N, num_horizons) - 每个样本在3个时间维度的标签
    """
    
    def __init__(
        self, 
        X: np.ndarray, 
        y: np.ndarray,
        normalizer: 'FeatureNormalizer' = None
    ):
        """
        Args:
            X: 特征序列 (N, seq_len, input_dim)
            y: 标签 (N, num_horizons)
            normalizer: 特征归一化器
        """
        assert len(X) == len(y), "X and y must have same length"
        
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)
        self.normalizer = normalizer
        
        if normalizer:
            self.X = normalizer.normalize_X(self.X)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


class FeatureNormalizer:
    """
    特征归一化器
    """
    
    def __init__(self, X: np.ndarray = None):
        self.mean = None
        self.std = None
        
        if X is not None:
            self.fit(X)
    
    def fit(self, X: np.ndarray):
        """计算均值和标准差"""
        # 对每个特征维度计算均值和标准差
        self.mean = np.mean(X, axis=(0, 1))  # (input_dim,)
        self.std = np.std(X, axis=(0, 1)) + 1e-8  # (input_dim,)
        
    def normalize_X(self, X: torch.Tensor) -> torch.Tensor:
        """归一化输入"""
        if self.mean is None:
            return X
        
        # X: (N, seq_len, input_dim)
        # mean, std: (input_dim,)
        mean = torch.tensor(self.mean, dtype=torch.float32)
        std = torch.tensor(self.std, dtype=torch.float32)
        
        return (X - mean.unsqueeze(0).unsqueeze(0)) / std.unsqueeze(0).unsqueeze(0)
    
    def denormalize_X(self, X: torch.Tensor) -> torch.Tensor:
        """反归一化"""
        if self.mean is None:
            return X
        
        mean = torch.tensor(self.mean, dtype=torch.float32)
        std = torch.tensor(self.std, dtype=torch.float32)
        
        return X * std.unsqueeze(0).unsqueeze(0) + mean.unsqueeze(0).unsqueeze(0)
    
    def save(self, path: Path):
        """保存归一化参数"""
        np.savez(path, mean=self.mean, std=self.std)
    
    @classmethod
    def load(cls, path: Path) -> 'FeatureNormalizer':
        """加载归一化参数"""
        data = np.load(path)
        normalizer = cls()
        normalizer.mean = data['mean']
        normalizer.std = data['std']
        return normalizer


class MLSCTrainer:
    """
    MLSC模型训练器
    
    特性:
    - 多任务学习: 同时优化3个时间维度的预测
    - 标签平滑: 防止过拟合
    - 学习率调度: ReduceLROnPlateau
    - Early Stopping: 防止过拟合
    - 梯度裁剪: 稳定训练
    """
    
    def __init__(
        self,
        config: MLSCConfig = None,
        device: str = None,
        model_path: str = 'output/mlsc_model.pth'
    ):
        self.config = config or MLSCConfig()
        self.device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
        self.model_path = Path(model_path)
        
        # 创建模型
        self.model = CNNAttentionGRU(
            input_dim=self.config.input_dim,
            seq_len=self.config.seq_len,
            cnn_out=self.config.cnn_out,
            num_heads=self.config.num_heads,
            gru_hidden=self.config.gru_hidden,
            num_classes=self.config.num_classes,
            num_horizons=self.config.num_horizons,
            dropout=self.config.dropout
        ).to(self.device)
        
        # 损失函数
        self.criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # 优化器
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=1e-3,
            weight_decay=1e-4
        )
        
        # 学习率调度器
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='max',
            patience=5,
            factor=0.5,
            min_lr=1e-6
        )
        
        # 训练状态
        self.best_val_acc = 0.0
        self.train_history = []
        self.val_history = []
        
        # 归一化器
        self.normalizer = None
        
    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str] = None,
        label_thresholds: Tuple[float, float] = (-0.02, 0.02)
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        从DataFrame准备训练数据
        
        Args:
            df: 包含历史数据的DataFrame
            feature_cols: 特征列名列表
            label_thresholds: 标签分类阈值 (上涨/下跌分界点)
            
        Returns:
            X: (N, seq_len, input_dim)
            y: (N, num_horizons)
        """
        if feature_cols is None:
            feature_cols = [
                'momentum_5d', 'volume_ratio', 'volatility_20d',
                'rsi', 'macd_signal', 'bb_position',
                'rank_change', 'turnover_rate', 'northbound_flow',
                'industry_strength'
            ]
        
        low_thresh, high_thresh = label_thresholds
        
        # 按股票分组
        stock_codes = df['stock_code'].unique()
        
        X_list = []
        y_list = []
        
        for stock_code in stock_codes:
            stock_df = df[df['stock_code'] == stock_code].sort_values('date')
            
            if len(stock_df) < self.config.seq_len + 5:
                continue
            
            # 提取特征序列
            for i in range(len(stock_df) - self.config.seq_len - 5):
                # 特征窗口
                seq = stock_df[feature_cols].iloc[i:i+self.config.seq_len].values
                X_list.append(seq)
                
                # 标签窗口 (基于未来N天的收益率)
                current_price = stock_df['close'].iloc[i + self.config.seq_len - 1]
                
                labels = []
                for offset, horizon in enumerate([1, 3, 5]):
                    future_idx = i + self.config.seq_len + offset
                    if future_idx >= len(stock_df):
                        future_idx = len(stock_df) - 1
                    
                    future_price = stock_df['close'].iloc[future_idx]
                    return_pct = (future_price - current_price) / current_price
                    
                    # 转换为标签
                    if return_pct > high_thresh:
                        label = 4 if return_pct > high_thresh * 2 else 3
                    elif return_pct < low_thresh:
                        label = 0 if return_pct < low_thresh * 2 else 1
                    else:
                        label = 2
                    
                    labels.append(label)
                
                y_list.append(labels)
        
        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.int64)
        
        print(f"[MLSCTrainer] Prepared {len(X)} samples")
        print(f"  Label distribution (1d): {np.bincount(y[:, 0], minlength=5)}")
        
        return X, y
    
    def prepare_data_from_csv(
        self,
        csv_path: str,
        seq_len: int = None,
        horizons: List[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        从CSV文件准备训练数据
        
        CSV格式:
        date, stock_code, open, high, low, close, volume, turnover_rate, ...
        """
        seq_len = seq_len or self.config.seq_len
        horizons = horizons or self.config.HORIZONS
        
        df = pd.read_csv(csv_path, parse_dates=['date'])
        
        # 基础特征
        df['change_pct'] = df.groupby('stock_code')['close'].pct_change()
        df['volume_ratio'] = df['volume'] / df.groupby('stock_code')['volume'].rolling(20).mean()
        df['volatility_20d'] = df.groupby('stock_code')['close'].pct_change().rolling(20).std()
        
        # 填充缺失值
        df = df.fillna(0)
        
        return self.prepare_data(df)
    
    def split_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15
    ) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        划分训练集/验证集/测试集 (按时间顺序)
        """
        n = len(X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        # 按时间顺序划分
        X_train, y_train = X[:train_end], y[:train_end]
        X_val, y_val = X[train_end:val_end], y[train_end:val_end]
        X_test, y_test = X[val_end:], y[val_end:]
        
        # 创建归一化器
        self.normalizer = FeatureNormalizer(X_train)
        
        # 创建数据集
        train_dataset = StockSequenceDataset(X_train, y_train, self.normalizer)
        val_dataset = StockSequenceDataset(X_val, y_val, self.normalizer)
        test_dataset = StockSequenceDataset(X_test, y_test, self.normalizer)
        
        print(f"\n[MLSCTrainer] Data split:")
        print(f"  Train: {len(train_dataset)} samples")
        print(f"  Val:   {len(val_dataset)} samples")
        print(f"  Test:  {len(test_dataset)} samples")
        
        train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)
        
        return train_loader, val_loader, test_loader
    
    def train_epoch(self, train_loader: DataLoader) -> Dict:
        """训练一个epoch"""
        self.model.train()
        
        total_loss = 0.0
        correct = np.zeros(self.config.num_horizons)
        total = np.zeros(self.config.num_horizons)
        
        for batch_X, batch_y in train_loader:
            batch_X = batch_X.to(self.device)
            batch_y = batch_y.to(self.device)
            
            self.optimizer.zero_grad()
            
            # 前向传播
            logits_list, _ = self.model(batch_X)
            
            # 计算多任务损失
            loss = 0
            for i, logits in enumerate(logits_list):
                loss += self.criterion(logits, batch_y[:, i])
            
            # 平均损失
            loss = loss / len(logits_list)
            
            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            
            # 计算准确率
            for i, logits in enumerate(logits_list):
                preds = logits.argmax(dim=1)
                correct[i] += (preds == batch_y[:, i]).sum().item()
                total[i] += len(batch_y)
        
        avg_loss = total_loss / len(train_loader)
        accuracies = correct / total
        
        return {
            'loss': avg_loss,
            'acc_1d': accuracies[0],
            'acc_3d': accuracies[1],
            'acc_5d': accuracies[2],
            'avg_acc': accuracies.mean()
        }
    
    @torch.no_grad()
    def validate(self, val_loader: DataLoader) -> Dict:
        """验证"""
        self.model.eval()
        
        total_loss = 0.0
        correct = np.zeros(self.config.num_horizons)
        total = np.zeros(self.config.num_horizons)
        
        for batch_X, batch_y in val_loader:
            batch_X = batch_X.to(self.device)
            batch_y = batch_y.to(self.device)
            
            logits_list, _ = self.model(batch_X)
            
            loss = sum(self.criterion(logits, batch_y[:, i]) for i, logits in enumerate(logits_list))
            loss = loss / len(logits_list)
            
            total_loss += loss.item()
            
            for i, logits in enumerate(logits_list):
                preds = logits.argmax(dim=1)
                correct[i] += (preds == batch_y[:, i]).sum().item()
                total[i] += len(batch_y)
        
        avg_loss = total_loss / len(val_loader)
        accuracies = correct / total
        
        return {
            'loss': avg_loss,
            'acc_1d': accuracies[0],
            'acc_3d': accuracies[1],
            'acc_5d': accuracies[2],
            'avg_acc': accuracies.mean()
        }
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 100,
        early_stop_patience: int = 15
    ) -> Dict:
        """
        训练模型
        
        Args:
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            epochs: 最大训练轮数
            early_stop_patience: 早停耐心值
        """
        print("\n" + "=" * 60)
        print("Starting MLSC Training")
        print("=" * 60)
        
        patience_counter = 0
        best_val_acc = 0.0
        
        for epoch in range(epochs):
            # 训练
            train_metrics = self.train_epoch(train_loader)
            self.train_history.append(train_metrics)
            
            # 验证
            val_metrics = self.validate(val_loader)
            self.val_history.append(val_metrics)
            
            # 学习率调度
            self.scheduler.step(val_metrics['avg_acc'])
            current_lr = self.optimizer.param_groups[0]['lr']
            
            # 打印进度
            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(f"\nEpoch {epoch+1}/{epochs} | LR: {current_lr:.6f}")
                print(f"  Train - Loss: {train_metrics['loss']:.4f}, "
                      f"Acc: {train_metrics['avg_acc']:.2%} "
                      f"(1d:{train_metrics['acc_1d']:.2%}, "
                      f"3d:{train_metrics['acc_3d']:.2%}, "
                      f"5d:{train_metrics['acc_5d']:.2%})")
                print(f"  Val   - Loss: {val_metrics['loss']:.4f}, "
                      f"Acc: {val_metrics['avg_acc']:.2%} "
                      f"(1d:{val_metrics['acc_1d']:.2%}, "
                      f"3d:{val_metrics['acc_3d']:.2%}, "
                      f"5d:{val_metrics['acc_5d']:.2%})")
            
            # 保存最佳模型
            if val_metrics['avg_acc'] > best_val_acc:
                best_val_acc = val_metrics['avg_acc']
                patience_counter = 0
                self._save_best_model()
            else:
                patience_counter += 1
            
            # 早停
            if patience_counter >= early_stop_patience:
                print(f"\n[MLSCTrainer] Early stopping at epoch {epoch+1}")
                break
        
        # 加载最佳模型
        self._load_best_model()
        
        return {
            'best_val_acc': best_val_acc,
            'epochs_trained': epoch + 1,
            'train_history': self.train_history,
            'val_history': self.val_history
        }
    
    def _save_best_model(self):
        """保存最佳模型"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'model_state_dict': self.model.state_dict(),
            'config': {
                'input_dim': self.config.input_dim,
                'seq_len': self.config.seq_len,
                'cnn_out': self.config.cnn_out,
                'num_heads': self.config.num_heads,
                'gru_hidden': self.config.gru_hidden,
                'num_classes': self.config.num_classes,
                'num_horizons': self.config.num_horizons,
                'dropout': self.config.dropout
            },
            'normalizer_mean': self.normalizer.mean if self.normalizer else None,
            'normalizer_std': self.normalizer.std if self.normalizer else None
        }
        
        torch.save(checkpoint, self.model_path)
    
    def _load_best_model(self):
        """加载最佳模型"""
        if self.model_path.exists():
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            print(f"[MLSCTrainer] Loaded best model from {self.model_path}")
    
    def evaluate(self, test_loader: DataLoader) -> Dict:
        """在测试集上评估模型"""
        self.model.eval()
        
        all_preds = {i: [] for i in range(self.config.num_horizons)}
        all_labels = {i: [] for i in range(self.config.num_horizons)}
        all_probs = {i: [] for i in range(self.config.num_horizons)}
        
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                batch_X = batch_X.to(self.device)
                
                logits_list, _ = self.model(batch_X)
                
                for i, logits in enumerate(logits_list):
                    probs = torch.softmax(logits, dim=1)
                    preds = logits.argmax(dim=1)
                    
                    all_preds[i].extend(preds.cpu().numpy())
                    all_labels[i].extend(batch_y[:, i].numpy())
                    all_probs[i].extend(probs.cpu().numpy())
        
        # 计算每个时间维度的指标
        results = {}
        horizons = self.config.HORIZONS
        
        for i, horizon in enumerate(horizons):
            from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
            
            y_true = np.array(all_labels[i])
            y_pred = np.array(all_preds[i])
            y_prob = np.array(all_probs[i])
            
            acc = accuracy_score(y_true, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true, y_pred, average='weighted'
            )
            
            # 混淆矩阵
            from sklearn.metrics import confusion_matrix
            cm = confusion_matrix(y_true, y_pred)
            
            results[horizon] = {
                'accuracy': acc,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'confusion_matrix': cm.tolist(),
                'predictions': y_pred.tolist(),
                'probabilities': y_prob.tolist()
            }
        
        return results
    
    def save_training_report(self, results: Dict, output_dir: str = 'output'):
        """保存训练报告"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config.__dict__,
            'best_val_accuracy': float(self.best_val_acc),
            'epochs_trained': len(self.train_history),
            'test_results': results,
            'train_history': [
                {k: float(v) for k, v in m.items()} for m in self.train_history
            ]
        }
        
        report_path = output_dir / 'mlsc_training_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n[MLSCTrainer] Training report saved to {report_path}")


def train_from_csv(csv_path: str, output_path: str = 'output/mlsc_model.pth'):
    """
    从CSV文件训练MLSC模型的便捷函数
    """
    trainer = MLSCTrainer(model_path=output_path)
    
    # 准备数据
    X, y = trainer.prepare_data_from_csv(csv_path)
    
    if len(X) < 100:
        print("[MLSCTrainer] Not enough data for training. Need at least 100 samples.")
        return None
    
    # 划分数据
    train_loader, val_loader, test_loader = trainer.split_data(X, y)
    
    # 训练
    train_results = trainer.train(train_loader, val_loader, epochs=100)
    
    # 评估
    test_results = trainer.evaluate(test_loader)
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print("\nTest Results:")
    for horizon, metrics in test_results.items():
        print(f"  {horizon}d - Accuracy: {metrics['accuracy']:.2%}, "
              f"F1: {metrics['f1']:.2%}")
    
    # 保存报告
    trainer.save_training_report(test_results)
    
    return trainer


if __name__ == '__main__':
    # 简单测试
    from .mlsc_model import create_sample_data
    
    print("=" * 60)
    print("MLSC Training Test")
    print("=" * 60)
    
    # 创建示例数据
    X, y = create_sample_data(seq_len=20)
    print(f"\nGenerated sample data:")
    print(f"  X shape: {X.shape}")
    print(f"  y shape: {y.shape}")
    
    # 创建训练器
    trainer = MLSCTrainer()
    
    # 划分数据
    train_loader, val_loader, test_loader = trainer.split_data(X, y)
    
    # 训练几个epoch测试
    results = trainer.train(train_loader, val_loader, epochs=10)
    
    print(f"\n[MLSCTrainer] Test completed!")
    print(f"  Best validation accuracy: {results['best_val_acc']:.2%}")
