# 02-Python规范

## 适用范围

适用于：

```text
app/worker
```

## 基础风格

遵守 PEP 8。

项目约定：

- 缩进使用 4 个空格
- 文件名使用 snake_case
- 函数名使用 snake_case
- 变量名使用 snake_case
- 类名使用 PascalCase
- 常量使用 UPPER_SNAKE_CASE

## 目录职责

```text
scripts/
  命令入口，只做参数解析和流程编排

src/
  业务逻辑
```

禁止把大量业务逻辑堆在 `scripts/*.py`。

## 函数规范

函数应该：

- 只做一件事
- 有清晰参数
- 有清晰返回值
- 必要时添加类型标注

示例：

```python
def calculate_momentum_score(close_prices: list[float]) -> float:
    ...
```

## 类型标注

新增 Python 代码尽量使用类型标注。

重点标注：

- 函数参数
- 函数返回值
- 复杂字典结构

## 异常处理

禁止：

```python
try:
    ...
except Exception:
    pass
```

必须：

- 记录日志
- 更新任务状态
- 必要时抛出异常或返回失败状态

## 数据写入

写 SQLite 必须使用事务。

批量写入失败时：

- 记录失败项
- 不覆盖旧数据
- 不让空结果清空表

## 脚本返回码

成功：

```text
exit code 0
```

失败：

```text
non-zero exit code
```

API Routes 会根据退出码判断任务成功或失败。

## 日志

worker 统一写 JSON Lines 日志。

禁止只用 `print` 作为错误处理。

`print` 只允许用于命令行进度提示，正式错误必须写日志。

## 注释规范

Python 注释用于解释业务规则和边界处理，不用于复述代码。

必须写注释的场景：

- MA20 / MA60 等指标计算的边界条件
- 收益率、波动率、最大回撤的计算口径
- 过滤 ST、停牌、低流动性的业务原因
- 非交易日使用最近交易日的处理
- 空数据不覆盖旧数据的保护逻辑
- SQLite 事务和写锁规避逻辑
- AkShare 返回字段兼容处理

推荐使用 docstring 的场景：

- 公共函数
- 数据源适配函数
- 因子计算函数
- 数据库写入函数

docstring 应说明：

- 函数做什么
- 输入是什么
- 输出是什么
- 关键边界条件

禁止：

- 保留和代码不一致的注释
- 用注释解释坏命名
- 注释掉大段废弃代码

修改因子口径、过滤规则、数据源适配、数据库写入逻辑时，必须同步更新注释和 docstring。
