# 奖励领取逻辑：数据库事务

effects = []


def claim(mail_id):
    effects.append(mail_id)  # bug: 每次调用都产生副作用
    return 100


def side_effect_count():
    return len(effects)
