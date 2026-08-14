# 奖励领取逻辑：数据库事务

rewards = {}


def claim(mail_id):
    if mail_id not in rewards:
        rewards[mail_id] = 100
    return rewards[mail_id]


def side_effect_count():
    return len(rewards)
