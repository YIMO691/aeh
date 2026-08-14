# 订单功能开发模块：重复提交控制

effects = []


def submit(order_id):
    effects.append(order_id)  # bug: 每次调用都产生副作用
    return 100


def side_effect_count():
    return len(effects)
