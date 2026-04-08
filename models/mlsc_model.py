# -*- coding: utf-8 -*-
"""
MLSC: Multi-Label Stock Classifier
多标签股票分类器 - 同时预测多时间维度趋势

参考论文: MLSC: A Multi-label Stock Classifier for Multi-horizon Stock Movement Prediction
架构: CNN + Multi-Head Attention + Bi-GRU
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass
class MLSCTPrediction:
    """MLSC单时间维度预测结果"""
    horizon: int                    # 预测时间维度: 1, 3, 5天
    trend: str                     # 趋势: 上涨/下跌/震荡
    confidence: float               # 置信度
    signal: str                     # 信号: 强烈买入/买入/持有/卖出/强烈卖出
    prob_distribution: Dict[str, float]  # 各类别概率分布
    
    def to_dict(self) -> dict:
        return {
            'horizon': self.horizon,
            'trend': self.trend,
            'confidence': round(self.confidence, 4),
            'signal': self.signal,
            'prob_distribution': {k: round(v, 4) for k, v in self.prob_distribution.items()}
        }


@dataclass
class MLSCConfig:
    """MLSC模型配置"""
    input_dim: int = 10            # 输入特征维度
    seq_len: int = 20              # 输入序列长度
    cnn_out: int = 64              # CNN输出维度
    num_heads: int = 4             # Attention头数
    gru_hidden: int = 128          # GRU隐藏层
    num_classes: int = 5           # 分类数
    num_horizons: int = 3          # 时间维度数
    dropout: float = 0.2           # Dropout比例
    
    # 标签定义
    LABELS = ['强烈卖出', '卖出', '持有', '买入', '强烈买入']
    HORIZONS = [1, 3, 5]           # 预测周期
    
    def save(self, path: Path):
        """保存配置到JSON"""
        config_dict = {
            'input_dim': self.input_dim,
            'seq_len': self.seq_len,
            'cnn_out': self.cnn_out,
            'num_heads': self.num_heads,
            'gru_hidden': self.gru_hidden,
            'num_classes': self.num_classes,
            'num_horizons': self.num_horizons,
            'dropout': self.dropout
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'MLSCConfig':
        """从JSON加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__annotations__})


class CNNAttentionGRU(nn.Module):
    """
    MLSC核心架构: CNN + Multi-Head Attention + Bi-GRU
    
    数据流:
    Input (batch, seq_len, input_dim)
        ↓
    CNN (局部特征提取)
        ↓
    Multi-Head Attention (长程依赖)
        ↓
    Bi-GRU (时序建模)
        ↓
    Dense Classifier × 3 (多任务输出)
        ↓
    Output: [1d预测, 3d预测, 5d预测]
    """
    
    def __init__(
        self,
        input_dim: int = 10,
        seq_len: int = 20,
        cnn_out: int = 64,
        num_heads: int = 4,
        gru_hidden: int = 128,
        num_classes: int = 5,
        num_horizons: int = 3,
        dropout: float = 0.2
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.seq_len = seq_len
        self.num_classes = num_classes
        self.num_horizons = num_horizons
        
        # 1. CNN层: 提取局部时空特征
        self.cnn = nn.Sequential(
            # 第一层CNN
            nn.Conv1d(input_dim, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(dropout),
            
            # 第二层CNN
            nn.Conv1d(32, cnn_out, kernel_size=3, padding=1),
            nn.BatchNorm1d(cnn_out),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # 2. Positional Encoding
        self.pos_encoding = self._create_positional_encoding(seq_len, cnn_out)
        
        # 3. Multi-Head Self-Attention
        self.attention = nn.MultiheadAttention(
            embed_dim=cnn_out,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        self.attention_norm = nn.LayerNorm(cnn_out)
        
        # 4. Feed-Forward Network
        self.ffn = nn.Sequential(
            nn.Linear(cnn_out, cnn_out * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(cnn_out * 4, cnn_out)
        )
        self.ffn_norm = nn.LayerNorm(cnn_out)
        
        # 5. Bi-GRU: 捕捉时序依赖
        self.gru = nn.GRU(
            input_size=cnn_out,
            hidden_size=gru_hidden,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if 2 > 1 else 0
        )
        
        # 6. 多任务输出头 (每个时间维度一个分类头)
        self.classifiers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(gru_hidden * 2, 128),
                nn.LayerNorm(128),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, num_classes)
            ) for _ in range(num_horizons)
        ])
        
        # 7. 趋势持续性预测头
        self.continuity_head = nn.Sequential(
            nn.Linear(gru_hidden * 2 * num_horizons, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        # 初始化权重
        self._init_weights()
    
    def _create_positional_encoding(self, max_len: int, d_model: int) -> torch.Tensor:
        """创建位置编码"""
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model > 1:
            pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
        return pe
    
    def _init_weights(self):
        """初始化权重"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Conv1d):
                nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
    
    def forward(
        self, 
        x: torch.Tensor,
        return_attention: bool = False
    ) -> Tuple[List[torch.Tensor], Optional[torch.Tensor]]:
        """
        前向传播
        
        Args:
            x: 输入张量 (batch_size, seq_len, input_dim)
            return_attention: 是否返回注意力权重
            
        Returns:
            logits_list: 每个时间维度的logits
            attention_weights: 注意力权重 (可选)
        """
        batch_size = x.size(0)
        
        # CNN: (batch, seq_len, input_dim) -> (batch, seq_len, cnn_out)
        x = x.transpose(1, 2)  # (batch, input_dim, seq_len)
        x = self.cnn(x)
        x = x.transpose(1, 2)  # (batch, seq_len, cnn_out)
        
        # 添加位置编码
        x = x + self.pos_encoding[:x.size(1)].unsqueeze(0)
        
        # Multi-Head Self-Attention with Residual
        attn_out, attn_weights = self.attention(x, x, x)
        x = self.attention_norm(x + attn_out)
        
        # Feed-Forward with Residual
        ffn_out = self.ffn(x)
        x = self.ffn_norm(x + ffn_out)
        
        # Bi-GRU
        gru_out, _ = self.gru(x)  # (batch, seq_len, gru_hidden * 2)
        
        # 取最后时刻的隐藏状态
        final_hidden = gru_out[:, -1, :]  # (batch, gru_hidden * 2)
        
        # 多任务分类输出
        logits_list = [classifier(final_hidden) for classifier in self.classifiers]
        
        # 趋势持续性预测
        if self.num_horizons > 1:
            all_features = torch.cat(
                [gru_out[:, -1, :] for _ in range(self.num_horizons)], 
                dim=1
            )
            continuity = self.continuity_head(all_features)  # (batch, 1)
        else:
            continuity = None
        
        if return_attention:
            return logits_list, continuity, attn_weights
        return logits_list, continuity
    
    def get_attention_weights(self, x: torch.Tensor) -> torch.Tensor:
        """获取注意力权重用于可视化"""
        with torch.no_grad():
            _, _, attn_weights = self.forward(x, return_attention=True)
        return attn_weights


class MLSCPredictor:
    """
    MLSC多标签股票分类器封装类
    
    用法示例:
        predictor = MLSCPredictor('output/mlsc_model.pth')
        result = predictor.predict(stock_history)
        print(result['consensus_signal'])
    """
    
    LABELS = ['强烈卖出', '卖出', '持有', '买入', '强烈买入']
    HORIZONS = [1, 3, 5]
    
    # 标签转趋势映射
    TREND_MAP = {
        0: '下跌',  # 强烈卖出
        1: '下跌',  # 卖出
        2: '震荡',
        3: '上涨',  # 买入
        4: '上涨'   # 强烈买入
    }
    
    def __init__(self, model_path: str = None, config: MLSCConfig = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.config = config or MLSCConfig()
        
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
        
        self.model.eval()
        self.is_loaded = False
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> bool:
        """加载预训练模型"""
        path = Path(model_path)
        if not path.exists():
            print(f"[MLSC] Model file not found: {model_path}")
            return False
        
        try:
            checkpoint = torch.load(path, map_location=self.device)
            
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.config = MLSCConfig(**checkpoint.get('config', {}))
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()
            self.is_loaded = True
            print(f"[MLSC] Model loaded from {model_path}")
            return True
            
        except Exception as e:
            print(f"[MLSC] Failed to load model: {e}")
            return False
    
    def save_model(self, model_path: str, **metadata):
        """保存模型"""
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
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
            'metadata': metadata
        }
        
        torch.save(checkpoint, path)
        self.config.save(path.with_suffix('.json'))
        print(f"[MLSC] Model saved to {model_path}")
    
    def prepare_features(self, stock_data: Dict) -> np.ndarray:
        """
        准备MLSC输入特征
        
        特征列表 (10维):
        1. 价格动量 (5日收益率)
        2. 成交量比率 (当前/20日均量)
        3. 波动率 (20日标准差)
        4. RSI (14日)
        5. MACD信号
        6. 布林带位置
        7. 人气排名变化
        8. 换手率
        9. 北向资金流向
        10. 行业相对强弱
        """
        features = []
        
        # 技术指标
        features.append(stock_data.get('momentum_5d', 0))
        features.append(stock_data.get('volume_ratio', 1))
        features.append(stock_data.get('volatility_20d', 0))
        features.append(stock_data.get('rsi', 50))
        features.append(stock_data.get('macd_signal', 0))
        features.append(stock_data.get('bb_position', 0.5))
        
        # 市场情绪
        features.append(stock_data.get('rank_change', 0))
        features.append(stock_data.get('turnover_rate', 0))
        
        # 资金流向
        features.append(stock_data.get('northbound_flow', 0))
        features.append(stock_data.get('industry_strength', 0))
        
        return np.array(features, dtype=np.float32)
    
    def prepare_sequence(
        self, 
        stock_history: List[Dict], 
        target_len: int = None
    ) -> np.ndarray:
        """
        准备输入序列
        
        Args:
            stock_history: 历史数据列表，每个元素是一个dict
            target_len: 目标序列长度
            
        Returns:
            np.ndarray: (1, seq_len, input_dim)
        """
        target_len = target_len or self.config.seq_len
        
        # 填充或截断到目标长度
        if len(stock_history) < target_len:
            # 填充: 用第一个数据复制
            padded = [stock_history[0]] * (target_len - len(stock_history)) + stock_history
        else:
            padded = stock_history[-target_len:]
        
        # 转换为特征矩阵
        features = [self.prepare_features(d) for d in padded]
        
        return np.array([features], dtype=np.float32)
    
    @torch.no_grad()
    def predict(self, stock_history: List[Dict]) -> Dict[int, MLSCTPrediction]:
        """
        预测多个时间维度的趋势
        
        Args:
            stock_history: 最近N天的股票数据列表
            
        Returns:
            Dict[int, MLSCTPrediction]: {1: 1天预测, 3: 3天预测, 5: 5天预测}
        """
        if not self.is_loaded:
            print("[MLSC] Warning: Model not loaded, returning default prediction")
            return self._default_prediction()
        
        # 准备输入
        X = self.prepare_sequence(stock_history)
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        
        # 推理
        logits_list, continuity = self.model(X_tensor)
        
        # 解析结果
        results = {}
        for i, (horizon, logits) in enumerate(zip(self.HORIZONS, logits_list)):
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_class = int(np.argmax(probs))
            
            results[horizon] = MLSCTPrediction(
                horizon=horizon,
                trend=self.TREND_MAP.get(pred_class, '震荡'),
                confidence=float(probs[pred_class]),
                signal=self.LABELS[pred_class],
                prob_distribution={
                    label: float(prob) 
                    for label, prob in zip(self.LABELS, probs)
                }
            )
        
        return results
    
    @torch.no_grad()
    def predict_with_continuity(self, stock_history: List[Dict]) -> Dict:
        """
        预测并返回趋势持续性
        
        Args:
            stock_history: 历史数据列表
            
        Returns:
            Dict: 包含各时间维度预测和趋势持续性
        """
        if not self.is_loaded:
            return self._default_prediction()
        
        X = self.prepare_sequence(stock_history)
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        
        logits_list, continuity = self.model(X_tensor)
        
        predictions = {}
        for horizon, logits in zip(self.HORIZONS, logits_list):
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_class = int(np.argmax(probs))
            
            predictions[horizon] = MLSCTPrediction(
                horizon=horizon,
                trend=self.TREND_MAP.get(pred_class, '震荡'),
                confidence=float(probs[pred_class]),
                signal=self.LABELS[pred_class],
                prob_distribution={
                    label: float(prob) 
                    for label, prob in zip(self.LABELS, probs)
                }
            )
        
        # 趋势持续性
        continuity_score = continuity.cpu().numpy()[0, 0] if continuity is not None else 0.5
        
        return {
            '1d_prediction': predictions[1],
            '3d_prediction': predictions[3],
            '5d_prediction': predictions[5],
            'continuity_score': float(continuity_score),
            'continuity_label': self._get_continuity_label(continuity_score)
        }
    
    def get_consensus_signal(self, predictions: Dict[int, MLSCTPrediction]) -> Dict:
        """
        综合多时间维度预测，生成一致性信号
        
        策略:
        - 短期(1d)和中期(3d)一致: 高置信度信号
        - 短期和长期(5d)矛盾: 趋势可能反转，谨慎信号
        - 三者一致: 强烈信号
        """
        signals = [p.signal for p in predictions.values()]
        confidences = [p.confidence for p in predictions.values()]
        avg_confidence = np.mean(confidences)
        
        # 信号强度映射
        strength_map = {
            '强烈卖出': -2, '卖出': -1, '持有': 0,
            '买入': 1, '强烈买入': 2
        }
        
        scores = [strength_map.get(s, 0) for s in signals]
        
        # 判断一致性
        if all(s > 0 for s in scores):
            consensus = '强烈买入' if avg_confidence > 0.7 else '买入'
            action = '建议买入'
        elif all(s < 0 for s in scores):
            consensus = '强烈卖出' if avg_confidence > 0.7 else '卖出'
            action = '建议卖出'
        elif scores[0] * scores[2] < 0:  # 短期和长期矛盾
            consensus = '趋势反转预警'
            action = '谨慎观望'
        else:
            consensus = '持有观望'
            action = '继续持有'
        
        return {
            'consensus_signal': consensus,
            'action_recommendation': action,
            'confidence': round(avg_confidence, 4),
            'signal_strength': sum(scores),
            'predictions': {k: v.to_dict() for k, v in predictions.items()},
            'trend_sustainability': self._calculate_sustainability(predictions),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_sustainability(self, predictions: Dict[int, MLSCTPrediction]) -> str:
        """计算趋势持续性"""
        trends = [p.trend for p in predictions.values()]
        
        if trends[0] == trends[1] == trends[2]:
            return '强持续性'
        elif trends[0] == trends[1]:
            return '中短期持续'
        elif trends[0] != trends[2]:
            return '可能反转'
        else:
            return '不确定性高'
    
    def _get_continuity_label(self, score: float) -> str:
        """持续性得分转标签"""
        if score > 0.8:
            return '强持续'
        elif score > 0.6:
            return '中等持续'
        elif score > 0.4:
            return '不确定'
        elif score > 0.2:
            return '可能减弱'
        else:
            return '即将反转'
    
    def _default_prediction(self) -> Dict[int, MLSCTPrediction]:
        """返回默认预测"""
        default_probs = [0.2, 0.2, 0.2, 0.2, 0.2]
        prob_dist = {label: p for label, p in zip(self.LABELS, default_probs)}
        
        results = {}
        for horizon in self.HORIZONS:
            results[horizon] = MLSCTPrediction(
                horizon=horizon,
                trend='震荡',
                confidence=0.2,
                signal='持有',
                prob_distribution=prob_dist
            )
        return results
    
    def explain_prediction(self, stock_history: List[Dict]) -> Dict:
        """
        生成预测解释
        
        Returns:
            包含预测结果和解释的字典
        """
        if not self.is_loaded:
            return {'error': 'Model not loaded'}
        
        predictions = self.predict(stock_history)
        consensus = self.get_consensus_signal(predictions)
        
        # 获取注意力权重
        X = self.prepare_sequence(stock_history)
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        attn_weights = self.model.get_attention_weights(X_tensor)
        
        # 分析重要的历史时间点
        avg_weights = attn_weights.mean(dim=1)[0].cpu().numpy()
        top_indices = np.argsort(avg_weights)[-3:][::-1]
        
        explanations = []
        for idx in top_indices:
            day_data = stock_history[idx] if idx < len(stock_history) else stock_history[0]
            explanations.append({
                'day_offset': idx - len(stock_history) + 1,
                'importance': float(avg_weights[idx]),
                'price_change': day_data.get('change_pct', 0),
                'volume_ratio': day_data.get('volume_ratio', 1)
            })
        
        return {
            'consensus': consensus,
            'attention_analysis': {
                'top_important_days': explanations,
                'interpretation': '这些日期的历史数据对当前预测影响最大'
            }
        }


def create_sample_data(seq_len: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    """
    创建示例训练数据
    
    Returns:
        X: (N, seq_len, 10) 特征序列
        y: (N, 3) 标签 (1d, 3d, 5d)
    """
    np.random.seed(42)
    N = 1000
    
    X = []
    y = []
    
    for _ in range(N):
        # 生成随机序列
        seq = np.random.randn(seq_len, 10).astype(np.float32)
        
        # 添加一些模式
        momentum = np.random.randn() * 0.1
        for i in range(seq_len):
            seq[i, 0] = momentum * (i / seq_len) + np.random.randn() * 0.05
        
        X.append(seq)
        
        # 生成标签 (基于最后几天的动量)
        end_momentum = np.mean(seq[-3:, 0])
        
        # 1天标签
        if end_momentum > 0.03:
            y_1d = 4
        elif end_momentum > 0.01:
            y_1d = 3
        elif end_momentum > -0.01:
            y_1d = 2
        elif end_momentum > -0.03:
            y_1d = 1
        else:
            y_1d = 0
        
        # 3天标签 (加入一些随机性)
        y_3d = max(0, min(4, y_1d + np.random.randint(-1, 2)))
        
        # 5天标签
        y_5d = max(0, min(4, y_1d + np.random.randint(-1, 2)))
        
        y.append([y_1d, y_3d, y_5d])
    
    return np.array(X), np.array(y)


if __name__ == '__main__':
    # 测试MLSC模型
    print("=" * 60)
    print("MLSC Multi-Label Stock Classifier Test")
    print("=" * 60)
    
    # 创建模型
    config = MLSCConfig()
    model = CNNAttentionGRU(
        input_dim=config.input_dim,
        seq_len=config.seq_len,
        num_classes=config.num_classes,
        num_horizons=config.num_horizons
    )
    
    print(f"\nModel Architecture:")
    print(f"  Input: (batch, {config.seq_len}, {config.input_dim})")
    print(f"  CNN Output: {config.cnn_out}")
    print(f"  Attention Heads: {config.num_heads}")
    print(f"  GRU Hidden: {config.gru_hidden}")
    print(f"  Output: {config.num_horizons} classifiers × {config.num_classes} classes")
    
    # 测试前向传播
    batch_size = 4
    X = torch.randn(batch_size, config.seq_len, config.input_dim)
    logits_list, continuity = model(X)
    
    print(f"\nForward Pass Test:")
    print(f"  Input shape: {X.shape}")
    for i, logits in enumerate(logits_list):
        print(f"  Horizon {config.HORIZONS[i]}d output: {logits.shape}")
    print(f"  Continuity: {continuity.shape if continuity is not None else 'None'}")
    
    # 测试预测器
    print("\n" + "=" * 60)
    print("Testing MLSCPredictor")
    print("=" * 60)
    
    predictor = MLSCPredictor()
    
    # 模拟历史数据
    sample_history = []
    for i in range(25):
        sample_history.append({
            'momentum_5d': np.random.randn() * 0.1,
            'volume_ratio': np.random.uniform(0.5, 2.0),
            'volatility_20d': np.random.uniform(0.01, 0.05),
            'rsi': np.random.uniform(20, 80),
            'macd_signal': np.random.randn() * 0.5,
            'bb_position': np.random.uniform(0, 1),
            'rank_change': np.random.uniform(-10, 10),
            'turnover_rate': np.random.uniform(1, 10),
            'northbound_flow': np.random.randn() * 100000000,
            'industry_strength': np.random.uniform(-1, 1)
        })
    
    # 由于模型未训练，返回默认预测
    predictions = predictor.predict(sample_history)
    
    print("\nSample Predictions:")
    for horizon, pred in predictions.items():
        print(f"  {horizon}d: {pred.signal} ({pred.trend}), confidence: {pred.confidence:.2%}")
    
    print("\nConsensus Signal:")
    consensus = predictor.get_consensus_signal(predictions)
    print(f"  Signal: {consensus['consensus_signal']}")
    print(f"  Action: {consensus['action_recommendation']}")
    print(f"  Confidence: {consensus['confidence']:.2%}")
    print(f"  Sustainability: {consensus['trend_sustainability']}")
    
    print("\n[MLSC] Test completed successfully!")
