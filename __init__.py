# -*- coding: utf-8 -*-
"""
项目主入口
Main Entry Point
"""

import logging
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from agents.orchestrator import Orchestrator
from memory import MemoryStore, ReflectionSystem
from history_store import HistoryStore
from config import SYSTEM_CONFIG


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print(f"{SYSTEM_CONFIG['name']} v{SYSTEM_CONFIG['version']}")
    print(f"{'='*60}\n")
    
    # 初始化系统
    print("初始化系统...")
    memory_store = MemoryStore()
    reflection_system = ReflectionSystem()
    history_store = HistoryStore()
    orchestrator = Orchestrator(memory_store)
    
    print("系统初始化完成！")
    print("\n可用的主要组件:")
    print("  - Orchestrator: 协调器，管理所有智能体")
    print("  - MemoryStore: 记忆存储，保存决策历史")
    print("  - ReflectionSystem: 反思系统，分析决策结果")
    print("  - HistoryStore: 历史数据存储")
    
    print("\n使用示例:")
    print("  from agents.orchestrator import Orchestrator")
    print("  orchestrator = Orchestrator()")
    print("  result = orchestrator.execute_analysis_pipeline(context)")
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
