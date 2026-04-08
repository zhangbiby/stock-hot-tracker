# -*- coding: utf-8 -*-
"""
Advanced Trading System
高级交易系统 - 集成MLSC、RL、回测、风控、WebSocket

用法:
    from advanced_features import AdvancedTradingSystem
    
    system = AdvancedTradingSystem()
    system.start()
"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import json

from models import MLSCPredictor, MLSCTPrediction
from rl import RLWeightAdapter, MarketState
from backtest import BacktestEngine, BacktestConfig
from risk import SmartRiskManager, RiskMetrics, RiskAlert, Position
from realtime import RealtimeSignalPusher, StockSignal, MarketStatus


class AdvancedTradingSystem:
    """
    高级交易系统
    
    集成:
    - MLSC多标签股票分类器
    - RL动态权重优化
    - 专业回测引擎
    - 智能风控系统
    - WebSocket实时推送
    """
    
    def __init__(
        self,
        config_path: str = 'config/advanced_config.json'
    ):
        """初始化高级交易系统"""
        self.config = self._load_config(config_path)
        
        # 子系统初始化
        self.mlsc_predictor: Optional[MLSCPredictor] = None
        self.rl_adapter: Optional[RLWeightAdapter] = None
        self.backtest_engine: Optional[BacktestEngine] = None
        self.risk_manager: Optional[SmartRiskManager] = None
        self.realtime_pusher: Optional[RealtimeSignalPusher] = None
        
        # 状态
        self.is_initialized = False
        self.is_running = False
        
        # 数据缓存
        self.stock_cache: Dict[str, List[Dict]] = {}
        self.current_signals: Dict[str, StockSignal] = {}
        
        # 回调函数
        self.on_signal_update: Optional[Callable] = None
        self.on_risk_alert: Optional[Callable] = None
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置"""
        default_config = {
            'mlsc': {
                'model_path': 'output/mlsc_model.pth',
                'enabled': True
            },
            'rl': {
                'model_path': 'output/rl_weight_model.zip',
                'enabled': True
            },
            'backtest': {
                'initial_capital': 1000000,
                'commission_rate': 0.0003,
                'slippage': 0.001
            },
            'risk': {
                'max_single_position': 0.15,
                'max_total_position': 0.85,
                'max_drawdown': 0.15
            },
            'realtime': {
                'host': '0.0.0.0',
                'port': 8765,
                'enabled': True
            }
        }
        
        path = Path(config_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # 合并配置
                for key in default_config:
                    if key in user_config:
                        default_config[key].update(user_config[key])
        
        return default_config
    
    def initialize(self):
        """初始化所有子系统"""
        print("\n" + "=" * 60)
        print("Initializing Advanced Trading System")
        print("=" * 60)
        
        # 1. 初始化MLSC预测器
        if self.config['mlsc']['enabled']:
            print("\n[1/5] Initializing MLSC Predictor...")
            try:
                self.mlsc_predictor = MLSCPredictor(
                    model_path=self.config['mlsc']['model_path']
                )
                print(f"  MLSC Predictor ready (loaded: {self.mlsc_predictor.is_loaded})")
            except Exception as e:
                print(f"  MLSC initialization failed: {e}")
                self.mlsc_predictor = MLSCPredictor()
        
        # 2. 初始化RL权重适配器
        if self.config['rl']['enabled']:
            print("\n[2/5] Initializing RL Weight Adapter...")
            try:
                self.rl_adapter = RLWeightAdapter(
                    model_path=self.config['rl']['model_path']
                )
                print("  RL Weight Adapter ready")
            except Exception as e:
                print(f"  RL initialization failed: {e}")
                self.rl_adapter = RLWeightAdapter()
        
        # 3. 初始化回测引擎
        print("\n[3/5] Initializing Backtest Engine...")
        backtest_config = BacktestConfig(
            initial_capital=self.config['backtest']['initial_capital'],
            commission_rate=self.config['backtest']['commission_rate'],
            slippage_rate=self.config['backtest']['slippage']
        )
        self.backtest_engine = BacktestEngine(backtest_config)
        print("  Backtest Engine ready")
        
        # 4. 初始化风控系统
        print("\n[4/5] Initializing Risk Manager...")
        self.risk_manager = SmartRiskManager(
            max_single_position=self.config['risk']['max_single_position'],
            max_total_position=self.config['risk']['max_total_position'],
            max_drawdown_limit=self.config['risk']['max_drawdown']
        )
        print("  Risk Manager ready")
        
        # 5. 初始化实时推送
        if self.config['realtime']['enabled']:
            print("\n[5/5] Initializing Realtime Pusher...")
            try:
                self.realtime_pusher = RealtimeSignalPusher(
                    ws_host=self.config['realtime']['host'],
                    ws_port=self.config['realtime']['port']
                )
                print(f"  Realtime Pusher ready (ws://{self.config['realtime']['host']}:{self.config['realtime']['port']})")
            except Exception as e:
                print(f"  Realtime initialization failed: {e}")
                self.realtime_pusher = None
        
        self.is_initialized = True
        print("\n" + "=" * 60)
        print("Advanced Trading System Initialized Successfully!")
        print("=" * 60)
    
    def start(self):
        """启动系统"""
        if not self.is_initialized:
            self.initialize()
        
        self.is_running = True
        print("\n[Advanced Trading System] Started")
    
    def stop(self):
        """停止系统"""
        self.is_running = False
        print("\n[Advanced Trading System] Stopped")
    
    # ==================== MLSC预测接口 ====================
    
    def predict_stock(self, stock_code: str, history: List[Dict]) -> Dict:
        """
        使用MLSC预测股票
        
        Args:
            stock_code: 股票代码
            history: 历史数据列表
            
        Returns:
            预测结果字典
        """
        if not self.mlsc_predictor:
            return {'error': 'MLSC Predictor not initialized'}
        
        # 缓存历史数据
        self.stock_cache[stock_code] = history
        
        # 进行预测
        predictions = self.mlsc_predictor.predict(history)
        consensus = self.mlsc_predictor.get_consensus_signal(predictions)
        
        return consensus
    
    # ==================== 风控接口 ====================
    
    def check_risk(self, positions: Dict[str, Position], market_data: Dict) -> Tuple[RiskMetrics, List[RiskAlert]]:
        """检查风险"""
        if not self.risk_manager:
            return RiskMetrics(), []
        
        portfolio_value = sum(p.market_value for p in positions.values())
        cash = 0  # 需要从外部传入
        
        self.risk_manager.update_positions(positions, portfolio_value, cash)
        return self.risk_manager.analyze_risk(market_data)
    
    def calculate_position_size(
        self,
        signal_strength: float,
        stock_volatility: float,
        available_capital: float
    ) -> float:
        """计算仓位"""
        if not self.risk_manager:
            return 0
        
        position_value, _ = self.risk_manager.get_position_size(
            signal_strength, stock_volatility, available_capital
        )
        return position_value
    
    # ==================== RL权重接口 ====================
    
    def get_adaptive_weights(
        self,
        index_change: float,
        volatility: float,
        volume_ratio: float,
        fear_greed: float
    ) -> Dict:
        """获取自适应权重"""
        if not self.rl_adapter:
            return self._default_weights()
        
        return self.rl_adapter.get_adaptive_weights(
            index_change, volatility, volume_ratio, fear_greed
        )
    
    def _default_weights(self) -> Dict:
        """默认权重"""
        return {
            'volume_price': 0.20,
            'rank_trend': 0.20,
            'technical': 0.20,
            'capital_flow': 0.15,
            'industry': 0.15,
            'sentiment': 0.05,
            'risk': 0.05
        }
    
    # ==================== 回测接口 ====================
    
    def run_backtest(
        self,
        data,
        signal_generator,
        start_date=None,
        end_date=None
    ):
        """运行回测"""
        if not self.backtest_engine:
            return None
        
        return self.backtest_engine.run(
            data, signal_generator, start_date, end_date
        )
    
    # ==================== 实时推送接口 ====================
    
    async def push_signal_async(self, signal: StockSignal):
        """异步推送信号"""
        if self.realtime_pusher:
            self.realtime_pusher.push_signal(signal)
    
    def push_signal(self, signal_data: dict):
        """推送信号 (同步)"""
        if self.realtime_pusher:
            signal = self.realtime_pusher.create_signal_from_dict(signal_data)
            asyncio.create_task(self.push_signal_async(signal))
    
    def push_market_status(self, status_data: dict):
        """推送市场状态"""
        if self.realtime_pusher:
            status = MarketStatus(
                index_name=status_data.get('index_name', '上证指数'),
                index_value=status_data.get('index_value', 0),
                change_pct=status_data.get('change_pct', 0),
                volume=status_data.get('volume', 0),
                market_mode=status_data.get('market_mode', 'sideways'),
                fear_greed_index=status_data.get('fear_greed_index', 50),
                northbound_flow=status_data.get('northbound_flow', 0)
            )
            self.realtime_pusher.push_market_status(status)
    
    # ==================== 综合分析接口 ====================
    
    def analyze_stock(self, stock_code: str, history: List[Dict], market_context: Dict) -> Dict:
        """
        综合分析股票
        
        整合MLSC预测、信号分析、市场状态
        
        Returns:
            综合分析报告
        """
        # 1. MLSC预测
        mlsc_result = self.predict_stock(stock_code, history)
        
        # 2. 获取自适应权重
        weights = self.get_adaptive_weights(
            index_change=market_context.get('index_change', 0),
            volatility=market_context.get('volatility', 0.02),
            volume_ratio=market_context.get('volume_ratio', 1.0),
            fear_greed=market_context.get('fear_greed', 50)
        )
        
        # 3. 整合结果
        report = {
            'stock_code': stock_code,
            'timestamp': datetime.now().isoformat(),
            'mlsc_prediction': mlsc_result,
            'adaptive_weights': weights,
            'recommendation': self._generate_recommendation(mlsc_result, weights),
            'risk_factors': self._analyze_risk_factors(history, market_context),
            'opportunity_factors': self._analyze_opportunity_factors(history, market_context)
        }
        
        return report
    
    def _generate_recommendation(self, mlsc_result: Dict, weights: Dict) -> Dict:
        """生成交易建议"""
        signal = mlsc_result.get('consensus_signal', '持有观望')
        confidence = mlsc_result.get('confidence', 0)
        
        if confidence > 0.75:
            if signal in ['强烈买入', '买入']:
                action = '积极买入'
                priority = 'high'
            elif signal in ['强烈卖出', '卖出']:
                action = '考虑减仓'
                priority = 'high'
            else:
                action = '观望'
                priority = 'medium'
        elif confidence > 0.5:
            action = '谨慎参与' if signal in ['买入', '强烈买入'] else '观望'
            priority = 'medium'
        else:
            action = '观望为主'
            priority = 'low'
        
        return {
            'action': action,
            'signal': signal,
            'confidence': confidence,
            'priority': priority
        }
    
    def _analyze_risk_factors(self, history: List[Dict], market_context: Dict) -> List[str]:
        """分析风险因素"""
        risks = []
        
        # 波动率风险
        if len(history) >= 20:
            recent_vol = np.std([h.get('change_pct', 0) for h in history[-10:]])
            if recent_vol > 0.03:
                risks.append('短期波动率偏高')
        
        # 流动性风险
        if history and history[-1].get('volume', 0) < 10000000:
            risks.append('成交量偏低，流动性风险')
        
        # 市场整体风险
        if market_context.get('index_change', 0) < -0.02:
            risks.append('大盘走势较弱')
        
        return risks
    
    def _analyze_opportunity_factors(self, history: List[Dict], market_context: Dict) -> List[str]:
        """分析机会因素"""
        opportunities = []
        
        # 趋势机会
        if len(history) >= 5:
            recent_changes = [h.get('change_pct', 0) for h in history[-5:]]
            if sum(recent_changes) > 0.05:
                opportunities.append('短期趋势向好')
        
        # 量价配合
        if history:
            last = history[-1]
            if last.get('volume_ratio', 1) > 1.5 and last.get('change_pct', 0) > 0:
                opportunities.append('量价齐升')
        
        return opportunities
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            'is_running': self.is_running,
            'is_initialized': self.is_initialized,
            'subsystems': {
                'mlsc': {
                    'available': self.mlsc_predictor is not None,
                    'loaded': self.mlsc_predictor.is_loaded if self.mlsc_predictor else False
                },
                'rl': {
                    'available': self.rl_adapter is not None,
                    'optimizations': len(self.rl_adapter.weight_history) if self.rl_adapter else 0
                },
                'backtest': {
                    'available': self.backtest_engine is not None
                },
                'risk': {
                    'available': self.risk_manager is not None,
                    'alerts_today': len([
                        a for a in (self.risk_manager.alert_history or [])
                        if a.timestamp.date() == datetime.now().date()
                    ]) if self.risk_manager else 0
                },
                'realtime': {
                    'available': self.realtime_pusher is not None,
                    'is_running': self.realtime_pusher.is_running if self.realtime_pusher else False
                }
            },
            'cache': {
                'stocks_cached': len(self.stock_cache),
                'signals_cached': len(self.current_signals)
            }
        }


# ==================== 便捷函数 ====================

def quick_analyze(stock_code: str, history: List[Dict], market_context: Dict = None) -> Dict:
    """
    快速分析股票
    
    便捷入口，不需要初始化完整系统
    """
    system = AdvancedTradingSystem()
    system.initialize()
    
    if market_context is None:
        market_context = {
            'index_change': 0,
            'volatility': 0.02,
            'volume_ratio': 1.0,
            'fear_greed': 50
        }
    
    return system.analyze_stock(stock_code, history, market_context)


def run_backtest_quick(data, signal_generator) -> 'BacktestResult':
    """快速回测"""
    system = AdvancedTradingSystem()
    system.initialize()
    return system.run_backtest(data, signal_generator)


# ==================== 主程序 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Advanced Trading System - Main Test")
    print("=" * 60)
    
    # 创建系统
    system = AdvancedTradingSystem()
    system.initialize()
    
    # 获取系统状态
    status = system.get_system_status()
    print("\nSystem Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 测试MLSC预测
    print("\n" + "=" * 60)
    print("Testing MLSC Prediction")
    print("=" * 60)
    
    import numpy as np
    
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
    
    # 预测
    result = system.predict_stock('000001', sample_history)
    print(f"\nMLSC Prediction for 000001:")
    print(f"  Consensus Signal: {result.get('consensus_signal')}")
    print(f"  Confidence: {result.get('confidence', 0):.2%}")
    print(f"  Sustainability: {result.get('trend_sustainability')}")
    
    # 测试风控
    print("\n" + "=" * 60)
    print("Testing Risk Management")
    print("=" * 60)
    
    from risk import Position
    
    positions = {
        '000001': Position(
            stock_code='000001',
            stock_name='平安银行',
            quantity=10000,
            avg_cost=12.0,
            current_price=12.5,
            entry_date=datetime.now(),
            sector='金融'
        )
    }
    
    market_data = {
        '000001': {'price': 12.5, 'volume': 50000000, 'volatility': 0.025, 'beta': 1.2}
    }
    
    metrics, alerts = system.check_risk(positions, market_data)
    print(f"\nRisk Metrics:")
    print(f"  VaR (95%): {metrics.var_95:.2%}")
    print(f"  Alerts: {len(alerts)}")
    
    # 测试自适应权重
    print("\n" + "=" * 60)
    print("Testing Adaptive Weights")
    print("=" * 60)
    
    weights = system.get_adaptive_weights(
        index_change=0.01,
        volatility=0.02,
        volume_ratio=1.2,
        fear_greed=65
    )
    
    print(f"\nAdaptive Weights (Bull Market):")
    for name, weight in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {name:15}: {weight:.2%}")
    
    print("\n" + "=" * 60)
    print("Advanced Trading System Test Complete!")
    print("=" * 60)
