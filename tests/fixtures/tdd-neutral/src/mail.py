# 订单邮件入口（功能开发模块）

from order import submit


def deliver(order_id):
    return submit(order_id)
