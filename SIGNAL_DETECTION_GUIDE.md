# 🎯 信号捕捉与AI对抗伪随机技术指南
# Signal Detection & AI vs Pseudo-Random Technical Guide

> **本文档是技术研究指南，详细说明如何捕捉伪随机信号、构建信号池和实现动态阈值控制**

**适用对象**: 机器学习研究者、数据科学家、AI工程师  
**技术水平**: 中级到高级  
**前置知识**: Python、机器学习基础、时序分析

---

## ⚠️ **使用声明 / Usage Declaration**

**本文档仅用于技术研究和学术交流！**

- ✅ 学习如何识别伪随机模式
- ✅ 理解AI特征工程方法
- ✅ 掌握信号处理技术
- ❌ **严禁用于赌博、博彩、彩票**

**详细免责声明请阅读**: [DISCLAIMER.md](DISCLAIMER.md)

---

## 📐 **系统参数 / System Parameters**

### 基础定义

```python
# 数据格式规范
BALL_RANGE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # 号码范围 0-9（共10个号码）
NUM_BALLS = 3  # 每期开3个球（有放回抽样）
SUM_MIN = 0    # 最小和值 (0+0+0)
SUM_MAX = 27   # 最大和值 (9+9+9)
SUM_MEDIAN = 13.5  # 中位数

# 大小奇偶定义
BIG_THRESHOLD = 14      # 和值 >= 14 为大
SMALL_THRESHOLD = 13    # 和值 <= 13 为小
# 奇偶：和值对2取模
```

### 理论概率

```python
# 单球概率
P_single_ball = 1 / 10 = 10%

# 大小概率（理论）
P_big = P_small = 50%

# 奇偶概率（理论）
P_odd = P_even = 50%

# 连续相同概率（理论）
P_consecutive_same = 1 / (10^3) = 0.1%
```

---

## 🔍 **信号捕捉方法 / Signal Detection Methods**

### 1. 趋势信号（Trend Signals）

**原理**: 检测短期趋势的延续性

#### 1.1 连续大小信号

```python
def detect_consecutive_size_trend(history, window=5):
    """
    检测连续大小趋势
    
    Args:
        history: 历史和值列表
        window: 观察窗口（期数）
    
    Returns:
        signal: 'BIG_STRONG' | 'SMALL_STRONG' | 'NEUTRAL'
    """
    recent = history[-window:]
    big_count = sum(1 for s in recent if s >= 14)
    small_count = window - big_count
    
    if big_count >= 4:  # 5期中至少4期是大
        return {
            'signal': 'BIG_STRONG',
            'confidence': big_count / window,
            'next_prediction': 'BIG',
            'reason': f'连续{big_count}期大，趋势延续'
        }
    elif small_count >= 4:
        return {
            'signal': 'SMALL_STRONG',
            'confidence': small_count / window,
            'next_prediction': 'SMALL',
            'reason': f'连续{small_count}期小，趋势延续'
        }
    else:
        return {'signal': 'NEUTRAL', 'confidence': 0.5}
```

#### 1.2 移动平均信号

```python
def detect_ma_trend(history, short_window=5, long_window=20):
    """
    双均线信号：短期均线 vs 长期均线
    
    金叉（Golden Cross）: 短均线上穿长均线 → BIG信号
    死叉（Death Cross）: 短均线下穿长均线 → SMALL信号
    """
    if len(history) < long_window:
        return {'signal': 'INSUFFICIENT_DATA'}
    
    ma_short = np.mean(history[-short_window:])
    ma_long = np.mean(history[-long_window:])
    
    # 检查趋势方向
    prev_ma_short = np.mean(history[-(short_window+1):-1])
    
    if ma_short > ma_long and prev_ma_short <= ma_long:
        return {
            'signal': 'GOLDEN_CROSS',
            'next_prediction': 'BIG',
            'ma_short': ma_short,
            'ma_long': ma_long,
            'strength': abs(ma_short - ma_long)
        }
    elif ma_short < ma_long and prev_ma_short >= ma_long:
        return {
            'signal': 'DEATH_CROSS',
            'next_prediction': 'SMALL',
            'ma_short': ma_short,
            'ma_long': ma_long,
            'strength': abs(ma_short - ma_long)
        }
    else:
        return {'signal': 'NO_CROSS'}
```

---

### 2. 反转信号（Reversal Signals）

**原理**: 检测极端偏离后的均值回归（Mean Reversion）

#### 2.1 偏离拉回信号

```python
def detect_mean_reversion(history, window=10, threshold=2.0):
    """
    检测偏离拉回信号
    
    当短期均值偏离长期均值超过阈值时，预测会拉回
    
    Args:
        threshold: 标准差倍数（如2.0表示2个标准差）
    """
    if len(history) < 50:
        return {'signal': 'INSUFFICIENT_DATA'}
    
    long_term_mean = np.mean(history[-50:])
    long_term_std = np.std(history[-50:])
    short_term_mean = np.mean(history[-window:])
    
    # 计算Z-score
    z_score = (short_term_mean - long_term_mean) / long_term_std
    
    if z_score > threshold:
        return {
            'signal': 'EXTREME_HIGH',
            'next_prediction': 'SMALL',  # 预测拉回
            'z_score': z_score,
            'confidence': min(abs(z_score) / 3, 0.9),  # Z=3时置信度90%
            'reason': f'短期均值{short_term_mean:.1f}显著高于长期{long_term_mean:.1f}'
        }
    elif z_score < -threshold:
        return {
            'signal': 'EXTREME_LOW',
            'next_prediction': 'BIG',  # 预测拉回
            'z_score': z_score,
            'confidence': min(abs(z_score) / 3, 0.9),
            'reason': f'短期均值{short_term_mean:.1f}显著低于长期{long_term_mean:.1f}'
        }
    else:
        return {'signal': 'NORMAL_RANGE', 'z_score': z_score}
```

#### 2.2 连续同向反转信号

```python
def detect_streak_exhaustion(history, max_streak=7):
    """
    检测连续同向疲劳信号
    
    连续7次以上大/小后，预测反转概率增加
    """
    streak_count = 0
    last_type = None
    
    for sum_val in reversed(history):
        current_type = 'BIG' if sum_val >= 14 else 'SMALL'
        
        if last_type is None:
            last_type = current_type
            streak_count = 1
        elif current_type == last_type:
            streak_count += 1
        else:
            break
    
    if streak_count >= max_streak:
        reverse_type = 'SMALL' if last_type == 'BIG' else 'BIG'
        return {
            'signal': 'STREAK_EXHAUSTION',
            'streak_count': streak_count,
            'current_type': last_type,
            'next_prediction': reverse_type,
            'confidence': min(0.5 + (streak_count - 7) * 0.05, 0.8),
            'reason': f'连续{streak_count}期{last_type}，疲劳反转'
        }
    else:
        return {'signal': 'NO_EXHAUSTION', 'streak_count': streak_count}
```

---

### 3. 形态信号（Pattern Signals）

**原理**: 识别特定的形态模式

#### 3.1 头肩顶/底信号

```python
def detect_head_shoulders(history, window=15):
    """
    检测头肩顶/底形态
    
    头肩顶: 左肩 < 头部 > 右肩 → 预测下跌（SMALL）
    头肩底: 左肩 > 头部 < 右肩 → 预测上涨（BIG）
    """
    if len(history) < window:
        return {'signal': 'INSUFFICIENT_DATA'}
    
    recent = history[-window:]
    
    # 简化的头肩检测：找三个局部极值点
    peaks = []
    troughs = []
    
    for i in range(1, len(recent) - 1):
        if recent[i] > recent[i-1] and recent[i] > recent[i+1]:
            peaks.append((i, recent[i]))
        elif recent[i] < recent[i-1] and recent[i] < recent[i+1]:
            troughs.append((i, recent[i]))
    
    # 头肩顶检测
    if len(peaks) >= 3:
        # 检查是否中间峰值最高
        sorted_peaks = sorted(peaks, key=lambda x: x[1], reverse=True)
        if sorted_peaks[0][0] > sorted_peaks[1][0] or sorted_peaks[0][0] > sorted_peaks[2][0]:
            return {
                'signal': 'HEAD_SHOULDERS_TOP',
                'next_prediction': 'SMALL',
                'confidence': 0.65,
                'pattern': 'Bearish reversal'
            }
    
    # 头肩底检测
    if len(troughs) >= 3:
        sorted_troughs = sorted(troughs, key=lambda x: x[1])
        if sorted_troughs[0][0] > sorted_troughs[1][0] or sorted_troughs[0][0] > sorted_troughs[2][0]:
            return {
                'signal': 'HEAD_SHOULDERS_BOTTOM',
                'next_prediction': 'BIG',
                'confidence': 0.65,
                'pattern': 'Bullish reversal'
            }
    
    return {'signal': 'NO_PATTERN'}
```

#### 3.2 周期性信号

```python
def detect_periodicity(history, test_periods=[50, 100, 200]):
    """
    检测周期性模式
    
    使用自相关函数（ACF）检测周期
    """
    from scipy import signal as sp_signal
    
    if len(history) < max(test_periods) * 2:
        return {'signal': 'INSUFFICIENT_DATA'}
    
    # 计算自相关
    acf_values = []
    for lag in test_periods:
        if len(history) > lag:
            corr = np.corrcoef(history[:-lag], history[lag:])[0, 1]
            acf_values.append((lag, corr))
    
    # 找最强周期
    strongest = max(acf_values, key=lambda x: abs(x[1]))
    lag, corr = strongest
    
    if abs(corr) > 0.3:  # 相关性阈值
        # 预测：查找lag期前的值
        if len(history) > lag:
            predicted_sum = history[-lag]
            return {
                'signal': 'PERIODIC_PATTERN',
                'period': lag,
                'correlation': corr,
                'next_prediction': 'BIG' if predicted_sum >= 14 else 'SMALL',
                'predicted_sum': predicted_sum,
                'confidence': abs(corr) * 0.7
            }
    
    return {'signal': 'NO_PERIODICITY'}
```

---

### 4. 卫兵信号（Guardian Signals）

**原理**: 过滤风险，防止错误信号

#### 4.1 方差检查

```python
def check_variance_stability(history, window=20):
    """
    检查方差稳定性
    
    如果近期方差异常（过大或过小），信号可能不可靠
    """
    if len(history) < window * 2:
        return {'status': 'INSUFFICIENT_DATA'}
    
    recent_var = np.var(history[-window:])
    baseline_var = np.var(history[-window*2:-window])
    
    var_ratio = recent_var / baseline_var if baseline_var > 0 else 0
    
    if var_ratio > 2.0:
        return {
            'status': 'HIGH_VOLATILITY',
            'warning': '近期波动异常增大，信号可能不可靠',
            'var_ratio': var_ratio,
            'risk_level': 'HIGH'
        }
    elif var_ratio < 0.5:
        return {
            'status': 'LOW_VOLATILITY',
            'warning': '近期波动异常减小，可能进入新状态',
            'var_ratio': var_ratio,
            'risk_level': 'MEDIUM'
        }
    else:
        return {
            'status': 'STABLE',
            'var_ratio': var_ratio,
            'risk_level': 'LOW'
        }
```

#### 4.2 连续失败检测

```python
def check_recent_accuracy(prediction_history, threshold=0.4):
    """
    检查近期预测准确率
    
    如果近10次准确率低于40%，停止发信号
    """
    if len(prediction_history) < 10:
        return {'status': 'INSUFFICIENT_DATA'}
    
    recent_10 = prediction_history[-10:]
    accuracy = sum(1 for p in recent_10 if p['correct']) / 10
    
    if accuracy < threshold:
        return {
            'status': 'POOR_PERFORMANCE',
            'accuracy': accuracy,
            'action': 'PAUSE_SIGNALS',
            'reason': f'近10次准确率{accuracy*100:.1f}%低于阈值{threshold*100}%'
        }
    else:
        return {
            'status': 'GOOD_PERFORMANCE',
            'accuracy': accuracy,
            'action': 'CONTINUE'
        }
```

---

## 🎛️ **信号池管理 / Signal Pool Management**

### 信号池架构

```python
class SignalPool:
    """
    信号池：管理多个信号源，动态调整权重
    """
    
    def __init__(self):
        self.signals = {}  # 信号字典
        self.weights = {}  # 权重字典（动态调整）
        self.performance = {}  # 性能记录
        
    def register_signal(self, name, detector_func, initial_weight=1.0):
        """注册信号检测器"""
        self.signals[name] = detector_func
        self.weights[name] = initial_weight
        self.performance[name] = {
            'total': 0,
            'correct': 0,
            'accuracy': 0.5
        }
    
    def detect_all(self, history):
        """运行所有信号检测器"""
        results = {}
        for name, detector in self.signals.items():
            try:
                results[name] = detector(history)
            except Exception as e:
                results[name] = {'signal': 'ERROR', 'error': str(e)}
        return results
    
    def aggregate_signals(self, signal_results):
        """
        信号聚合：加权投票
        
        返回最终预测和置信度
        """
        votes = {'BIG': 0, 'SMALL': 0, 'NEUTRAL': 0}
        total_weight = 0
        
        for name, result in signal_results.items():
            if 'next_prediction' in result:
                prediction = result['next_prediction']
                confidence = result.get('confidence', 0.5)
                weight = self.weights[name]
                
                # 加权投票
                votes[prediction] += confidence * weight
                total_weight += weight
        
        if total_weight == 0:
            return {'prediction': 'NEUTRAL', 'confidence': 0.5}
        
        # 归一化
        for key in votes:
            votes[key] /= total_weight
        
        # 选择最强信号
        winner = max(votes, key=votes.get)
        confidence = votes[winner]
        
        return {
            'prediction': winner,
            'confidence': confidence,
            'votes': votes,
            'signal_count': len(signal_results)
        }
    
    def update_performance(self, name, correct):
        """更新信号性能"""
        perf = self.performance[name]
        perf['total'] += 1
        if correct:
            perf['correct'] += 1
        perf['accuracy'] = perf['correct'] / perf['total']
        
        # 动态调整权重
        self._adjust_weight(name)
    
    def _adjust_weight(self, name):
        """
        动态权重调整策略
        
        准确率越高，权重越大
        """
        accuracy = self.performance[name]['accuracy']
        
        if accuracy > 0.6:
            # 优秀信号：增加权重
            self.weights[name] = min(2.0, 1.0 + (accuracy - 0.6) * 2)
        elif accuracy < 0.4:
            # 差劲信号：降低权重
            self.weights[name] = max(0.1, accuracy / 0.4)
        else:
            # 一般信号：保持基础权重
            self.weights[name] = 1.0
    
    def get_performance_report(self):
        """生成性能报告"""
        report = []
        for name, perf in self.performance.items():
            report.append({
                'signal': name,
                'accuracy': f"{perf['accuracy']*100:.2f}%",
                'correct': perf['correct'],
                'total': perf['total'],
                'weight': f"{self.weights[name]:.2f}"
            })
        return sorted(report, key=lambda x: float(x['accuracy'][:-1]), reverse=True)
```

### 使用示例

```python
# 初始化信号池
pool = SignalPool()

# 注册信号
pool.register_signal('consecutive_trend', detect_consecutive_size_trend, initial_weight=1.0)
pool.register_signal('ma_trend', detect_ma_trend, initial_weight=1.0)
pool.register_signal('mean_reversion', detect_mean_reversion, initial_weight=1.2)
pool.register_signal('streak_exhaustion', detect_streak_exhaustion, initial_weight=0.8)
pool.register_signal('periodicity', detect_periodicity, initial_weight=0.9)

# 检测信号
history = [14, 15, 18, 20, 22, 16, 15, 13, 12, 10, 9, 11, 13, 14, 16]
signal_results = pool.detect_all(history)

# 聚合信号
final_prediction = pool.aggregate_signals(signal_results)
print(f"最终预测: {final_prediction['prediction']}, 置信度: {final_prediction['confidence']:.2%}")

# 验证结果（假设实际开奖和值为17）
actual_sum = 17
actual_type = 'BIG' if actual_sum >= 14 else 'SMALL'
correct = (actual_type == final_prediction['prediction'])

# 更新所有信号的性能
for name in signal_results:
    pool.update_performance(name, correct)

# 查看性能报告
print(pool.get_performance_report())
```

---

## 📊 **动态阈值控制 / Dynamic Threshold Control**

### 1. 自适应置信度阈值

```python
class DynamicThreshold:
    """
    动态阈值控制器
    
    根据近期表现自动调整置信度阈值
    """
    
    def __init__(self, initial_threshold=0.6):
        self.threshold = initial_threshold
        self.min_threshold = 0.55
        self.max_threshold = 0.85
        self.performance_window = 20
        self.history = []
    
    def should_act(self, confidence, prediction):
        """
        判断是否应该执行动作
        
        Args:
            confidence: 信号置信度
            prediction: 预测结果
        
        Returns:
            bool: 是否应该执行
        """
        if confidence >= self.threshold:
            self.history.append({
                'confidence': confidence,
                'prediction': prediction,
                'acted': True
            })
            return True
        else:
            return False
    
    def update(self, correct):
        """
        更新最后一次动作的结果
        
        Args:
            correct: 预测是否正确
        """
        if len(self.history) > 0:
            self.history[-1]['correct'] = correct
            self._adjust_threshold()
    
    def _adjust_threshold(self):
        """
        动态调整阈值
        
        策略：
        - 准确率高：降低阈值（更激进）
        - 准确率低：提高阈值（更保守）
        """
        if len(self.history) < 10:
            return
        
        recent = self.history[-self.performance_window:]
        acted = [h for h in recent if h.get('acted', False)]
        
        if len(acted) < 5:
            return
        
        accuracy = sum(1 for h in acted if h.get('correct', False)) / len(acted)
        
        if accuracy > 0.65:
            # 表现优秀：降低阈值5%
            self.threshold = max(self.min_threshold, self.threshold - 0.05)
        elif accuracy < 0.50:
            # 表现不佳：提高阈值5%
            self.threshold = min(self.max_threshold, self.threshold + 0.05)
        # accuracy在0.50-0.65之间：保持不变
    
    def get_status(self):
        """获取当前状态"""
        recent = self.history[-20:]
        acted = [h for h in recent if h.get('acted', False)]
        
        if len(acted) >= 5:
            accuracy = sum(1 for h in acted if h.get('correct', False)) / len(acted)
        else:
            accuracy = 0.5
        
        return {
            'threshold': self.threshold,
            'recent_accuracy': f"{accuracy*100:.2f}%",
            'action_count': len(acted),
            'total_signals': len(recent)
        }
```

### 2. 覆盖率控制

```python
class CoverageController:
    """
    覆盖率控制器
    
    确保每日动作数量在合理范围内
    """
    
    def __init__(self, target_coverage=(0.25, 0.40), periods_per_day=324):
        """
        Args:
            target_coverage: 目标覆盖率范围（如25%-40%）
            periods_per_day: 每日期数（平均324期）
        """
        self.target_min = target_coverage[0]
        self.target_max = target_coverage[1]
        self.periods_per_day = periods_per_day
        self.daily_actions = 0
        self.daily_periods = 0
    
    def can_act(self, confidence):
        """
        判断是否可以执行动作（考虑覆盖率限制）
        """
        current_coverage = self.daily_actions / max(self.daily_periods, 1)
        
        # 如果已超过最大覆盖率，只接受极高置信度信号
        if current_coverage >= self.target_max:
            return confidence >= 0.85
        
        # 如果低于最小覆盖率，降低要求
        if current_coverage < self.target_min and self.daily_periods > 100:
            return confidence >= 0.55
        
        # 正常范围
        return confidence >= 0.60
    
    def record_action(self, acted):
        """记录动作"""
        self.daily_periods += 1
        if acted:
            self.daily_actions += 1
    
    def reset_daily(self):
        """每日重置"""
        coverage = self.daily_actions / max(self.daily_periods, 1)
        self.daily_actions = 0
        self.daily_periods = 0
        return coverage
    
    def get_status(self):
        """获取当前状态"""
        coverage = self.daily_actions / max(self.daily_periods, 1)
        return {
            'current_coverage': f"{coverage*100:.2f}%",
            'target_range': f"{self.target_min*100:.0f}%-{self.target_max*100:.0f}%",
            'actions_today': self.daily_actions,
            'periods_today': self.daily_periods,
            'remaining_capacity': int((self.target_max - coverage) * self.periods_per_day)
        }
```

### 3. 综合控制系统

```python
class SignalController:
    """
    综合信号控制系统
    
    整合信号池、动态阈值和覆盖率控制
    """
    
    def __init__(self):
        self.signal_pool = SignalPool()
        self.dynamic_threshold = DynamicThreshold(initial_threshold=0.60)
        self.coverage_controller = CoverageController()
        self.guardian_checks = []
        
    def add_guardian(self, check_func):
        """添加卫兵检查"""
        self.guardian_checks.append(check_func)
    
    def process_new_draw(self, history, new_draw=None):
        """
        处理新的一期数据
        
        Args:
            history: 历史数据（不包括新一期）
            new_draw: 新一期的结果（如果已开奖，用于验证）
        
        Returns:
            decision: 是否执行动作及预测内容
        """
        # 1. 检测所有信号
        signal_results = self.signal_pool.detect_all(history)
        
        # 2. 聚合信号
        prediction = self.signal_pool.aggregate_signals(signal_results)
        
        # 3. 卫兵检查
        for check in self.guardian_checks:
            guard_result = check(history)
            if guard_result.get('risk_level') == 'HIGH':
                return {
                    'action': 'NO_ACTION',
                    'reason': guard_result.get('warning'),
                    'prediction': prediction
                }
        
        # 4. 动态阈值检查
        confidence = prediction['confidence']
        should_act_threshold = self.dynamic_threshold.should_act(confidence, prediction['prediction'])
        
        # 5. 覆盖率控制
        should_act_coverage = self.coverage_controller.can_act(confidence)
        
        # 6. 综合决策
        final_action = should_act_threshold and should_act_coverage
        
        self.coverage_controller.record_action(final_action)
        
        decision = {
            'action': 'ACT' if final_action else 'NO_ACTION',
            'prediction': prediction['prediction'],
            'confidence': confidence,
            'threshold': self.dynamic_threshold.threshold,
            'coverage_status': self.coverage_controller.get_status(),
            'signal_details': signal_results
        }
        
        # 7. 如果已开奖，更新性能
        if new_draw is not None:
            actual_sum = sum(new_draw)
            actual_type = 'BIG' if actual_sum >= 14 else 'SMALL'
            correct = (actual_type == prediction['prediction'])
            
            if final_action:
                self.dynamic_threshold.update(correct)
                for name in signal_results:
                    self.signal_pool.update_performance(name, correct)
        
        return decision
```

---

## 🚀 **完整示例 / Complete Example**

```python
import numpy as np
from datetime import datetime

# 初始化系统
controller = SignalController()

# 注册信号
controller.signal_pool.register_signal('consecutive_trend', detect_consecutive_size_trend, 1.0)
controller.signal_pool.register_signal('ma_trend', detect_ma_trend, 1.0)
controller.signal_pool.register_signal('mean_reversion', detect_mean_reversion, 1.2)
controller.signal_pool.register_signal('streak_exhaustion', detect_streak_exhaustion, 0.8)

# 添加卫兵
controller.add_guardian(check_variance_stability)

# 模拟实时运行
history = []  # 从BigQuery加载历史数据

# 实时循环
while True:
    # 获取最新历史数据
    # history = fetch_from_bigquery()  # 实际从BigQuery读取
    
    # 处理决策
    decision = controller.process_new_draw(history)
    
    print(f"\n{'='*60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"动作: {decision['action']}")
    print(f"预测: {decision['prediction']}")
    print(f"置信度: {decision['confidence']:.2%}")
    print(f"当前阈值: {decision['threshold']:.2%}")
    print(f"覆盖率状态: {decision['coverage_status']}")
    
    if decision['action'] == 'ACT':
        print(f"\n🎯 执行动作！预测下一期: {decision['prediction']}")
        # 这里可以记录到BigQuery的actions表
    
    # 等待下一期开奖
    # time.sleep(180)  # 等待3分钟
    
    # 获取实际结果并更新
    # new_draw = fetch_latest_draw()
    # controller.process_new_draw(history, new_draw)
```

---

## 📈 **性能评估 / Performance Evaluation**

### KPI指标

```python
class PerformanceMetrics:
    """
    性能评估指标
    """
    
    @staticmethod
    def calculate_accuracy(predictions, actuals):
        """准确率"""
        correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
        return correct / len(predictions)
    
    @staticmethod
    def calculate_coverage(total_predictions, total_periods):
        """覆盖率"""
        return total_predictions / total_periods
    
    @staticmethod
    def calculate_ev(accuracy, payout=1.95):
        """
        期望值（Expected Value）
        
        EV = accuracy × payout - (1 - accuracy) × 1
        """
        return accuracy * payout - (1 - accuracy)
    
    @staticmethod
    def calculate_sharpe_ratio(returns):
        """
        夏普比率（风险调整收益）
        """
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        return mean_return / std_return if std_return > 0 else 0
    
    @staticmethod
    def generate_report(prediction_history):
        """生成完整报告"""
        predictions = [h['prediction'] for h in prediction_history]
        actuals = [h['actual'] for h in prediction_history]
        
        accuracy = PerformanceMetrics.calculate_accuracy(predictions, actuals)
        ev = PerformanceMetrics.calculate_ev(accuracy)
        
        returns = [1.95 if p == a else -1 for p, a in zip(predictions, actuals)]
        sharpe = PerformanceMetrics.calculate_sharpe_ratio(returns)
        
        return {
            'accuracy': f"{accuracy*100:.2f}%",
            'ev': f"{ev:.4f}",
            'sharpe_ratio': f"{sharpe:.4f}",
            'total_predictions': len(predictions),
            'total_return': sum(returns),
            'win_rate': accuracy,
            'break_even_required': 51.28
        }
```

---

## ⚠️ **重要提醒 / Important Reminders**

### 技术研究目的

本文档中的所有技术**仅适用于伪随机算法研究**：

1. ✅ **学习目的** - 理解信号处理和AI应用
2. ✅ **研究目的** - 探索伪随机模式识别
3. ✅ **教育目的** - 提升数据科学技能
4. ❌ **禁止用于真实彩票** - 真随机无法预测
5. ❌ **禁止用于赌博** - 违法且必然亏损

### 真随机 vs 伪随机

| 特征 | 伪随机（本项目） | 真随机（真实彩票） |
|-----|----------------|------------------|
| 信号有效性 | ✅ 部分有效（研究价值） | ❌ 完全无效 |
| AI准确率 | 52-55% (理论) | 50% (无法提升) |
| 偏移检测 | ✅ 可检测 | ❌ 无偏移 |
| 研究价值 | ✅ 高 | ❌ 无 |
| 盈利可能 | ❌ 无（研究项目） | ❌ 无（必然亏损） |

---

## 📚 **推荐阅读 / Recommended Reading**

1. **时序分析**
   - "Time Series Analysis" by James D. Hamilton
   - "Forecasting: Principles and Practice" by Rob J Hyndman

2. **机器学习**
   - "Hands-On Machine Learning" by Aurélien Géron
   - Scikit-learn Documentation

3. **信号处理**
   - "Digital Signal Processing" by John G. Proakis
   - SciPy Signal Processing Tutorial

---

**最后更新**: 2025-10-07  
**版本**: v1.0  
**状态**: ✅ 技术研究文档

**联系**: 仅限技术问题，GitHub Issues  
**禁止**: 任何赌博、博彩、投注相关咨询

---

**声明**: 本文档所有技术仅用于伪随机算法研究和学术交流。严禁将本文档用于任何赌博、博彩、彩票预测或其他非法用途。使用者需自行承担所有法律和经济责任。详见 [DISCLAIMER.md](DISCLAIMER.md)

