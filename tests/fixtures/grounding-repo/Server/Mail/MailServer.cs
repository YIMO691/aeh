public class MailServer { // 领取奖励入口
    void ReceiveMail(string mailId) {
        ReceiveReward.Claim(mailId);
    }
}