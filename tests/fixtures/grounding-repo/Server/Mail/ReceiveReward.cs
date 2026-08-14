public class ReceiveReward { // 奖励领取逻辑：数据库事务
    void Claim(string mailId) {
        // reward logic with database transaction
        Database.Save(reward);
        GrantReward(mailId);
    }
    void GrantReward(string id) { }
}