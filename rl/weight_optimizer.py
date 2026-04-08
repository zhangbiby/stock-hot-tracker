# -*- coding: utf-8 -*-
"""
RL Weight Optimizer
基于强化学习的因子权重动态调整系统

使用PPO算法根据市场状态自动优化信号引擎的因子权重
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import gym

# 尝试导入stable-baselines3
try:
    from stable_baselines3 import PPO, A2C, SAC
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    from stable_baselines3.common.callbacks import EvalCallback, EarlyStoppingCallback
    STABLE_BASELINES_AVAILABLE = True
except ImportError:
    STABLE_BASELINES_AVAILABLE = False
    print("[RLWeightOptimizer] stable-baselines3 not installed. RL features disabled.")
    print("[RLWeightOptimizer] Install with: pip install stable-baselines3")


# 因子名称定义
FACTOR_NAMES = [
    'volume_price',    # 量价配合
    'rank_trend',      # 人气趋势
    'technical',       # 技术指标
    'capital_flow',    # 资金流向
    'industry',        # 行业效应
    'sentiment',       # 情绪分析
    'risk'             # 风险控制
]

# 默认因子权重
DEFAULT_WEIGHTS = {
    'volume_price': 0.20,
    'rank_trend': 0.20,
    'technical': 0.20,
    'capital_flow': 0.15,
    'industry': 0.15,
    'sentiment': 0.10,
    'risk': 0.00
}


@dataclass
class MarketState:
    """市场状态"""
    trend_strength: float      # 趋势强度 [-1, 1]
    volatility: float           # 波动率 [0, 1]
    volume_ratio: float         # 量比 [0, +∞)
    breadth: float              # 市场广度 [0, 1]
    fear_greed: float           # 恐慌贪婪指数 [0, 100]
    market_mode: str            # 市场模式: 'bull', 'bear', 'sideways'
    
    def to_array(self) -> np.ndarray:
        """转换为特征数组"""
        return np.array([
            self.trend_strength,
            self.volatility,
            self.volume_ratio,
            self.breadth,
            self.fear_greed / 100.0,  # 归一化到[0,1]
            1.0 if self.market_mode == 'bull' else 0.0,
            1.0 if self.market_mode == 'bear' else 0.0,
            1.0 if self.market_mode == 'sideways' else 0.0
        ], dtype=np.float32)


@dataclass
class TradingMetrics:
    """交易指标"""
    recent_returns: List[float]     # 近期收益率列表
    win_rate: float                  # 胜率
    avg_win: float                   # 平均盈利
    avg_loss: float                  # 平均亏损
    sharpe_ratio: float              # 夏普比率
    max_drawdown: float              # 最大回撤
    current_weights: Dict[str, float] # 当前权重


@dataclass
class RLExperience:
    """RL经验数据"""
    timestamp: datetime
    market_state: MarketState
    weights: Dict[str, float]
    reward: float
    next_market_state: Optional[MarketState]
    done: bool


class FactorWeightEnv(gym.Env if STABLE_BASELINES_AVAILABLE else object):
    """
    因子权重优化Gym环境
    
    状态空间: 市场状态特征 (8维)
    动作空间: 7个因子的权重调整系数 (连续)
    
    使用PPO算法学习最优的动态权重调整策略
    """
    
    metadata = {'render.modes': ['human']}
    
    def __init__(
        self,
        signal_engine = None,
        market_data_buffer: List[MarketState] = None,
        max_steps: int = 252,
        initial_capital: float = 1000000.0
    ):
        """
        Args:
            signal_engine: 信号引擎实例 (可选)
            market_data_buffer: 市场状态历史数据
            max_steps: 最大步数 (交易日)
            initial_capital: 初始资金
        """
        if not STABLE_BASELINES_AVAILABLE:
            raise ImportError("stable-baselines3 is required for RL features")
        
        super().__init__()
        
        self.signal_engine = signal_engine
        self.market_data = market_data_buffer or []
        self.max_steps = max_steps
        self.initial_capital = initial_capital
        
        # 状态空间: 市场状态特征 (8维)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(8,), dtype=np.float32
        )
        
        # 动作空间: 7个因子的权重调整 (连续)
        # 动作值范围 [-1, 1]，表示相对于当前权重的调整幅度
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0, shape=(len(FACTOR_NAMES),), dtype=np.float32
        )
        
        # 初始化
        self.current_step = 0
        self.current_weights = DEFAULT_WEIGHTS.copy()
        self.capital = initial_capital
        self.position_history = []
        self.experience_buffer: List[RLExperience] = []
        
        # 奖励计算所需数据
        self.price_history = []
        self.signal_history = []
        
    def reset(self) -> np.ndarray:
        """重置环境"""
        self.current_step = 0
        self.current_weights = DEFAULT_WEIGHTS.copy()
        self.capital = self.initial_capital
        self.position_history = []
        
        return self._get_observation()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行一步
        
        Args:
            action: 权重调整系数 (7维, [-1, 1])
            
        Returns:
            observation: 下一个状态
            reward: 奖励
            done: 是否结束
            info: 额外信息
        """
        # 1. 应用动作，调整权重
        self._apply_action(action)
        
        # 2. 获取奖励
        reward = self._calculate_reward()
        
        # 3. 更新状态
        self.current_step += 1
        done = self.current_step >= self.max_steps
        
        # 4. 获取下一个观察
        if done:
            observation = np.zeros(8, dtype=np.float32)
        else:
            observation = self._get_observation()
        
        # 5. 记录经验
        current_state = self._get_current_market_state()
        self.experience_buffer.append(RLExperience(
            timestamp=datetime.now(),
            market_state=current_state,
            weights=self.current_weights.copy(),
            reward=reward,
            next_market_state=None,
            done=done
        ))
        
        info = {
            'weights': self.current_weights.copy(),
            'capital': self.capital,
            'step': self.current_step
        }
        
        return observation, reward, done, info
    
    def _apply_action(self, action: np.ndarray):
        """
        将动作转换为新的因子权重
        
        策略:
        1. 将动作值从[-1,1]映射到[0,1]
        2. 使用指数移动平均平滑调整
        3. 归一化确保权重和为1
        """
        # 平滑系数
        smooth_factor = 0.3
        
        # 计算调整量
        adjustment = (action + 1) / 2  # 映射到[0, 1]
        
        # 应用平滑调整
        new_values = []
        for i, name in enumerate(FACTOR_NAMES):
            current_val = self.current_weights.get(name, 0.1)
            adjusted_val = adjustment[i]
            
            # 指数移动平均
            new_val = current_val * (1 - smooth_factor) + adjusted_val * smooth_factor
            
            # 限制最小权重
            new_val = max(0.05, min(0.5, new_val))
            new_values.append(new_val)
        
        # 归一化到总和为1
        total = sum(new_values)
        self.current_weights = {
            name: val / total 
            for name, val in zip(FACTOR_NAMES, new_values)
        }
        
        # 更新信号引擎的权重 (如果可用)
        if self.signal_engine:
            self.signal_engine.set_factor_weights(self.current_weights)
    
    def _get_observation(self) -> np.ndarray:
        """获取当前观察"""
        state = self._get_current_market_state()
        
        # 添加当前权重作为观察的一部分
        weight_values = list(self.current_weights.values())
        
        # 组合市场状态和权重
        observation = np.concatenate([
            state.to_array(),
            np.array(weight_values, dtype=np.float32)
        ])
        
        return observation
    
    def _get_current_market_state(self) -> MarketState:
        """获取当前市场状态"""
        if self.current_step < len(self.market_data):
            return self.market_data[self.current_step]
        
        # 生成模拟市场状态
        return MarketState(
            trend_strength=np.random.uniform(-0.5, 0.5),
            volatility=np.random.uniform(0.1, 0.5),
            volume_ratio=np.random.uniform(0.5, 2.0),
            breadth=np.random.uniform(0.3, 0.7),
            fear_greed=np.random.uniform(20, 80),
            market_mode=np.random.choice(['bull', 'bear', 'sideways'])
        )
    
    def _calculate_reward(self) -> float:
        """
        计算奖励
        
        综合考虑:
        - 收益率
        - 夏普比率
        - 最大回撤
        - 胜率
        """
        if len(self.price_history) < 5:
            return 0.0
        
        returns = self.price_history[-20:]  # 最近20期收益
        if len(returns) < 2:
            return 0.0
        
        returns = np.array(returns)
        
        # 1. 基础收益率奖励
        total_return = np.sum(returns)
        return_reward = total_return * 100  # 放大100倍
        
        # 2. 夏普比率奖励
        if np.std(returns) > 0:
            sharpe = np.mean(returns) / (np.std(returns) + 1e-6)
            sharpe_reward = sharpe * 0.5
        else:
            sharpe_reward = 0
        
        # 3. 回撤惩罚
        drawdown = self._calculate_drawdown(returns)
        drawdown_penalty = -drawdown * 3
        
        # 4. 权重稳定性奖励 (避免频繁调整)
        weight_change = self._calculate_weight_change()
        stability_reward = -weight_change * 0.1
        
        # 综合奖励
        total_reward = return_reward + sharpe_reward + drawdown_penalty + stability_reward
        
        return total_reward
    
    def _calculate_drawdown(self, returns: np.ndarray) -> float:
        """计算最大回撤"""
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / (peak + 1e-6)
        return np.min(drawdown)
    
    def _calculate_weight_change(self) -> float:
        """计算权重变化"""
        if len(self.experience_buffer) < 2:
            return 0.0
        
        prev_weights = self.experience_buffer[-2].weights
        curr_weights = self.current_weights
        
        changes = [
            abs(curr_weights.get(k, 0) - prev_weights.get(k, 0))
            for k in FACTOR_NAMES
        ]
        
        return sum(changes)
    
    def add_price_data(self, price_change: float, signal_result: Dict = None):
        """添加价格数据"""
        self.price_history.append(price_change)
        
        if signal_result:
            self.signal_history.append(signal_result)
    
    def add_market_state(self, state: MarketState):
        """添加市场状态数据"""
        self.market_data.append(state)
    
    def get_metrics(self) -> TradingMetrics:
        """获取当前交易指标"""
        returns = self.price_history[-20:] if self.price_history else []
        
        if len(returns) < 2:
            return TradingMetrics(
                recent_returns=returns,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                current_weights=self.current_weights.copy()
            )
        
        returns = np.array(returns)
        
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        
        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = abs(np.mean(losses)) if len(losses) > 0 else 0
        
        sharpe = np.mean(returns) / (np.std(returns) + 1e-6) if np.std(returns) > 0 else 0
        
        return TradingMetrics(
            recent_returns=returns.tolist(),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            sharpe_ratio=sharpe,
            max_drawdown=self._calculate_drawdown(returns),
            current_weights=self.current_weights.copy()
        )
    
    def render(self, mode='human'):
        """渲染环境状态"""
        metrics = self.get_metrics()
        
        print(f"\n=== RL Weight Optimizer State ===")
        print(f"Step: {self.current_step}/{self.max_steps}")
        print(f"Capital: {self.capital:,.2f}")
        print(f"\nFactor Weights:")
        for name, weight in sorted(self.current_weights.items(), key=lambda x: -x[1]):
            print(f"  {name:15}: {weight:.2%}")
        print(f"\nMetrics:")
        print(f"  Win Rate:    {metrics.win_rate:.2%}")
        print(f"  Sharpe:      {metrics.sharpe_ratio:.3f}")
        print(f"  Max Drawdown: {metrics.max_drawdown:.2%}")


class RLWeightOptimizer:
    """
    RL权重优化器主类
    
    使用强化学习自动优化信号引擎的因子权重
    """
    
    def __init__(
        self,
        model_path: str = None,
        algorithm: str = 'PPO',
        total_timesteps: int = 100000
    ):
        """
        Args:
            model_path: 预训练模型路径
            algorithm: 算法选择 ('PPO', 'A2C', 'SAC')
            total_timesteps: 训练总步数
        """
        if not STABLE_BASELINES_AVAILABLE:
            raise ImportError("stable-baselines3 is required")
        
        self.model = None
        self.model_path = model_path
        self.algorithm = algorithm
        self.total_timesteps = total_timesteps
        
        self.training_history = []
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def create_env(self, signal_engine=None, market_data=None) -> gym.Env:
        """创建环境"""
        return FactorWeightEnv(
            signal_engine=signal_engine,
            market_data_buffer=market_data
        )
    
    def train(
        self,
        signal_engine=None,
        market_data: List[MarketState] = None,
        eval_freq: int = 10000,
        save_freq: int = 20000
    ) -> Dict:
        """
        训练RL模型
        
        Args:
            signal_engine: 信号引擎实例
            market_data: 市场状态历史数据
            eval_freq: 评估频率
            save_freq: 保存频率
            
        Returns:
            训练结果字典
        """
        print("\n" + "=" * 60)
        print(f"RL Weight Optimizer Training ({self.algorithm})")
        print("=" * 60)
        
        # 创建环境
        env = DummyVecEnv([lambda: self.create_env(signal_engine, market_data)])
        
        # 创建模型
        if self.algorithm == 'PPO':
            self.model = PPO(
                "MlpPolicy",
                env,
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,
                verbose=1
            )
        elif self.algorithm == 'A2C':
            self.model = A2C(
                "MlpPolicy",
                env,
                learning_rate=3e-4,
                n_steps=20,
                gamma=0.99,
                verbose=1
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
        
        # 训练
        self.model.learn(
            total_timesteps=self.total_timesteps,
            progress_bar=True
        )
        
        # 保存模型
        if self.model_path:
            self.save_model(self.model_path)
        
        return {
            'status': 'completed',
            'total_timesteps': self.total_timesteps,
            'model_path': self.model_path
        }
    
    def optimize_weights(self, market_state: MarketState, current_weights: Dict = None) -> Dict:
        """
        使用训练好的模型优化权重
        
        Args:
            market_state: 当前市场状态
            current_weights: 当前权重
            
        Returns:
            优化后的权重
        """
        if self.model is None:
            return current_weights or DEFAULT_WEIGHTS.copy()
        
        # 准备观测
        observation = np.concatenate([
            market_state.to_array(),
            np.array(list((current_weights or DEFAULT_WEIGHTS).values()), dtype=np.float32)
        ])
        
        # 预测动作
        action, _ = self.model.predict(observation, deterministic=True)
        
        # 将动作转换为权重
        adjustment = (action + 1) / 2  # 映射到[0, 1]
        
        values = []
        for i, name in enumerate(FACTOR_NAMES):
            current_val = (current_weights or DEFAULT_WEIGHTS).get(name, 0.1)
            adjusted_val = adjustment[i]
            
            # 平滑调整
            new_val = current_val * 0.7 + adjusted_val * 0.3 * 0.5
            new_val = max(0.05, min(0.5, new_val))
            values.append(new_val)
        
        # 归一化
        total = sum(values)
        optimized_weights = {
            name: val / total 
            for name, val in zip(FACTOR_NAMES, values)
        }
        
        return optimized_weights
    
    def save_model(self, path: str):
        """保存模型"""
        if self.model is None:
            return
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        self.model.save(str(path))
        
        # 保存配置
        config = {
            'algorithm': self.algorithm,
            'factor_names': FACTOR_NAMES,
            'default_weights': DEFAULT_WEIGHTS
        }
        
        with open(path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"[RLWeightOptimizer] Model saved to {path}")
    
    def load_model(self, path: str) -> bool:
        """加载模型"""
        if not STABLE_BASELINES_AVAILABLE:
            return False
        
        path = Path(path)
        if not path.exists():
            print(f"[RLWeightOptimizer] Model not found: {path}")
            return False
        
        try:
            if self.algorithm == 'PPO':
                self.model = PPO.load(str(path))
            elif self.algorithm == 'A2C':
                self.model = A2C.load(str(path))
            
            print(f"[RLWeightOptimizer] Model loaded from {path}")
            return True
            
        except Exception as e:
            print(f"[RLWeightOptimizer] Failed to load model: {e}")
            return False


class RLWeightAdapter:
    """
    RL权重适配器 - 集成到现有信号引擎
    
    用法:
        adapter = RLWeightAdapter('output/rl_weight_model.zip')
        optimized_weights = adapter.optimize_weights(market_state)
        signal_engine.set_factor_weights(optimized_weights)
    """
    
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: 预训练模型路径
        """
        self.optimizer = RLWeightOptimizer(model_path=model_path)
        self.weight_history = []
        self.performance_history = []
    
    def optimize_weights(
        self, 
        market_state: MarketState,
        current_weights: Dict = None
    ) -> Dict:
        """
        优化权重
        
        Args:
            market_state: 当前市场状态
            current_weights: 当前使用的权重
            
        Returns:
            优化后的权重
        """
        optimized = self.optimizer.optimize_weights(
            market_state,
            current_weights
        )
        
        # 记录历史
        self.weight_history.append({
            'timestamp': datetime.now(),
            'weights': optimized,
            'market_state': market_state.market_mode
        })
        
        return optimized
    
    def get_adaptive_weights(
        self,
        index_change: float,
        volatility: float,
        volume_ratio: float,
        fear_greed: float
    ) -> Dict:
        """
        根据市场指标生成自适应权重
        
        这是一个简化的快速版本，不需要完整的市场状态对象
        """
        # 确定市场模式
        if index_change > 0.01 and fear_greed > 60:
            market_mode = 'bull'
        elif index_change < -0.01 and fear_greed < 40:
            market_mode = 'bear'
        else:
            market_mode = 'sideways'
        
        # 根据市场模式设置基础权重
        if market_mode == 'bull':
            # 牛市: 增加量价和技术权重
            base_weights = {
                'volume_price': 0.25,
                'rank_trend': 0.20,
                'technical': 0.25,
                'capital_flow': 0.10,
                'industry': 0.10,
                'sentiment': 0.05,
                'risk': 0.05
            }
        elif market_mode == 'bear':
            # 熊市: 增加风险和情绪权重
            base_weights = {
                'volume_price': 0.15,
                'rank_trend': 0.15,
                'technical': 0.15,
                'capital_flow': 0.15,
                'industry': 0.10,
                'sentiment': 0.15,
                'risk': 0.15
            }
        else:
            # 震荡: 均衡权重
            base_weights = {
                'volume_price': 0.20,
                'rank_trend': 0.20,
                'technical': 0.20,
                'capital_flow': 0.15,
                'industry': 0.15,
                'sentiment': 0.05,
                'risk': 0.05
            }
        
        # 根据波动率调整
        vol_factor = min(volatility / 0.03, 2.0)  # 波动率高于3%时增加风险权重
        
        adjusted_weights = base_weights.copy()
        adjusted_weights['risk'] = min(0.2, adjusted_weights['risk'] * vol_factor)
        adjusted_weights['technical'] = adjusted_weights['technical'] / (1 + vol_factor * 0.2)
        
        # 归一化
        total = sum(adjusted_weights.values())
        adjusted_weights = {k: v / total for k, v in adjusted_weights.items()}
        
        # 如果有RL模型，进一步优化
        if self.optimizer.model is not None:
            state = MarketState(
                trend_strength=index_change * 10,
                volatility=volatility,
                volume_ratio=volume_ratio,
                breadth=0.5,
                fear_greed=fear_greed,
                market_mode=market_mode
            )
            adjusted_weights = self.optimize_weights(state, adjusted_weights)
        
        return adjusted_weights
    
    def get_statistics(self) -> Dict:
        """获取优化统计"""
        if not self.weight_history:
            return {}
        
        recent_weights = [h['weights'] for h in self.weight_history[-20:]]
        
        # 计算权重变化
        changes = []
        for i in range(1, len(recent_weights)):
            prev = recent_weights[i-1]
            curr = recent_weights[i]
            change = sum(abs(curr[k] - prev.get(k, 0)) for k in FACTOR_NAMES)
            changes.append(change)
        
        return {
            'total_optimizations': len(self.weight_history),
            'avg_weight_change': np.mean(changes) if changes else 0,
            'weight_volatility': np.std(changes) if changes else 0,
            'recent_modes': [h['market_state'] for h in self.weight_history[-10:]]
        }
    
    def export_weights_log(self, path: str):
        """导出权重日志"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write("timestamp,market_mode," + ",".join(FACTOR_NAMES) + "\n")
            
            for entry in self.weight_history:
                timestamp = entry['timestamp'].isoformat()
                mode = entry['market_state']
                weights = entry['weights']
                weight_str = ",".join(str(weights.get(k, 0)) for k in FACTOR_NAMES)
                f.write(f"{timestamp},{mode},{weight_str}\n")
        
        print(f"[RLWeightAdapter] Weights log exported to {path}")


def create_sample_market_data(n_samples: int = 500) -> List[MarketState]:
    """创建示例市场数据"""
    np.random.seed(42)
    
    market_modes = ['bull', 'bear', 'sideways']
    market_data = []
    
    for i in range(n_samples):
        mode = np.random.choice(market_modes, p=[0.3, 0.3, 0.4])
        
        if mode == 'bull':
            trend = np.random.uniform(0.2, 0.8)
        elif mode == 'bear':
            trend = np.random.uniform(-0.8, -0.2)
        else:
            trend = np.random.uniform(-0.3, 0.3)
        
        state = MarketState(
            trend_strength=trend,
            volatility=np.random.uniform(0.1, 0.4),
            volume_ratio=np.random.uniform(0.5, 2.0),
            breadth=np.random.uniform(0.3, 0.7),
            fear_greed=np.random.uniform(20, 80),
            market_mode=mode
        )
        
        market_data.append(state)
    
    return market_data


if __name__ == '__main__':
    print("=" * 60)
    print("RL Weight Optimizer Test")
    print("=" * 60)
    
    if not STABLE_BASELINES_AVAILABLE:
        print("\n[ERROR] stable-baselines3 not installed")
        print("RL features are disabled")
        exit(1)
    
    # 测试环境
    print("\nTesting FactorWeightEnv...")
    env = FactorWeightEnv()
    
    obs = env.reset()
    print(f"Initial observation shape: {obs.shape}")
    print(f"Observation space: {env.observation_space}")
    print(f"Action space: {env.action_space}")
    
    # 测试一步
    action = env.action_space.sample()
    obs, reward, done, info = env.step(action)
    
    print(f"\nAfter one step:")
    print(f"  Reward: {reward:.4f}")
    print(f"  Done: {done}")
    print(f"  Weights: {info['weights']}")
    
    # 测试适配器
    print("\n" + "=" * 60)
    print("Testing RLWeightAdapter (Fast Mode)...")
    print("=" * 60)
    
    adapter = RLWeightAdapter()
    
    # 测试不同市场状态
    test_cases = [
        {'index_change': 0.02, 'volatility': 0.02, 'volume_ratio': 1.5, 'fear_greed': 70},
        {'index_change': -0.03, 'volatility': 0.05, 'volume_ratio': 0.8, 'fear_greed': 25},
        {'index_change': 0.00, 'volatility': 0.01, 'volume_ratio': 1.0, 'fear_greed': 50},
    ]
    
    for i, case in enumerate(test_cases):
        weights = adapter.get_adaptive_weights(**case)
        print(f"\nCase {i+1}: Index change={case['index_change']:+.1%}, "
              f"Volatility={case['volatility']:.1%}")
        print("  Optimized weights:")
        for name, weight in sorted(weights.items(), key=lambda x: -x[1]):
            print(f"    {name:15}: {weight:.2%}")
    
    print("\n[RL Weight Optimizer] Test completed!")
