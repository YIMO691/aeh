# 订单重复提交控制

orders = {}


def submit(order_id):
    if order_id not in orders:
        orders[order_id] = 100
    return orders[order_id]


def side_effect_count():
    return len(orders)
