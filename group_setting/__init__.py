from telegram_util import matchKey, getDisplayUser, splitCommand
import yaml

# TODO: once stabled, mark setting as gitignore
# TODO: see if I want to accept command without '/'
# TODO: for blacklist ban, scan through all member

class Setting(object):
    def __init__(self, raw):
        self.delete_if_message_is_forward = (
            raw.get('delete_if_message_is_forward', True))
        self.greeting = raw.get('greeting')
        self.delete_join_left = raw.get('delete_join_left', True)
        self.kick_if_name_longer_than = raw.get('kick_if_name_longer_than', 0)
        self.kick_if_name_contains = raw.get('kick_if_name_contains', [])
        self.warning_on_message_delete = raw.get('warning_on_message_delete')

    def shouldKick(self, user):
        if (self.kick_if_name_longer_than and 
            len(user.first_name or '') + len(user.last_name or '') > 
                self.kick_if_name_longer_than):
            return True
        if matchKey(getDisplayUser(user), self.kick_if_name_contains):
            return True
        return False

    def update(self, text):
        command, text = splitCommand(text)

        if 'delete_if_message_is_forward' in command:
            if 'delete_if_message_is_forward_on' in command:
                self.delete_if_message_is_forward = True
            if 'delete_if_message_is_forward_off' in command:
                self.delete_if_message_is_forward = False
            return 'delete_if_message_is_forward: ' + str(self.delete_if_message_is_forward)

        if 'delete_join_left_message' in command:
            if 'delete_join_left_message_on' in command:
                self.delete_join_left = True
            if 'delete_join_left_message_off' in command:
                self.delete_join_left = False
            return 'delete_join_left_message: ' + str(self.delete_join_left)

        if 'welcome_message' in command:
            if 'welcome_message_off' in command:
                self.greeting = ''
            if 'welcome_message_set' in command:
                self.greeting = text
            if self.greeting:
                return 'welcome_message: ' + self.greeting
            else:
                return 'no welcome mesage'

        if 'warning_on_message_delete' in command:
            if 'warning_on_message_delete_off' in command:
                self.warning_on_message_delete = ''
            if 'warning_on_message_delete_set' in command:
                self.warning_on_message_delete = text
            if self.warning_on_message_delete:
                return 'warning_on_message_delete: ' + self.warning_on_message_delete
            else:
                return 'no warning on message delete'
        # warning_on_message_delete_off - hide warning when bot delete user's message
        # warning_on_message_delete_set - set warning message when bot delete user's message
        # kick_if_name_longer_than_off - turn off kick_if_name_longer_than
        # kick_if_name_longer_than_set - kick if name longer than how many characters

        if 'kick_if_name_longer_than' in command:
            if 'kick_if_name_longer_than_off' in command:
                self.kick_if_name_longer_than = 0
            if 'kick_if_name_longer_than_set' in command:
                

        if 'kick_if_name_contains_status' in text:
            return 'kick_if_name_contains: ' + str(self.kick_if_name_contains)
        
        if 'kick_if_name_longer_than_status' in text:
            if self.kick_if_name_longer_than:
                return 'kick if name longer than %d characters' % self.kick_if_name_longer_than
            else:
                return 'kick_if_name_longer_than not set'


# kick_if_name_contains_add - add word to username blacklist
# kick_if_name_contains_remove - remove word from username blacklist

class GroupSetting(object):
    def __init__(self):
        with open('group_setting/SETTING') as f:
            self.setting = yaml.load(f, Loader=yaml.FullLoader)

    def get(self, chat_id):
        return self.greeting.get(chat_id, '欢迎新朋友！新朋友请自我介绍~')

    def setGreeting(self, chat_id, text):
        self.greeting[chat_id] = text
        self.save()

    def setDisableModeration(self, chat_id, b):
        if not b and chat_id in self.disable_moderation:
            self.disable_moderation.remove(chat_id)
        if b and not chat_id in self.disable_moderation:
            self.disable_moderation.append(chat_id)
            self.disable_moderation.sort()
        self.save()

    def isModerationDisabled(self, chat_id):
        return chat_id in self.disable_moderation

    def save(self):
        with open('db/SETTING', 'w') as f:
            f.write(yaml.dump({
                'greeting': self.greeting, 
                'disable_moderation': self.disable_moderation,
            }, sort_keys=True, indent=2))
        commit()

class DB(object):
    lists = ['KICKLIST', 'MUTELIST', 'WHITELIST']

    def readFile(self, filename):
        with open('db/' + filename) as f:
            content = [x.strip() for x in f.readlines()]
            setattr(self, filename, set([x for x in content if x]))

    def saveFile(self, filename):
        with open('db/' + filename, 'w') as f:
            f.write('\n'.join(sorted(getattr(self, filename))))

    def __init__(self):
        for l in self.lists:
            self.readFile(l)
        with open('db/BLACKLIST') as f:
            lines = [x.strip().split(':') for x in f.readlines() if x.strip()]
        self.BLACKLIST = {line[0].strip().lower(): float(line[1]) 
            for line in lines if line[0] and line[0].strip()}

    def saveBlacklist(self):
        lines = [(k.strip().lower(), v) for (k, v) in self.BLACKLIST.items() 
            if k and k.strip()]
        lines = sorted([('%s: %f' % l).rstrip('0').rstrip('.') for l in lines])
        with open('db/BLACKLIST', 'w') as f:
            f.write('\n'.join(lines))
        commit()

    def reduceBadness(self, text):
        text = text.strip()
        if not text:
            return 'no action'
        text = text.lower()
        if text not in self.BLACKLIST:
            return 'no action'
        self.BLACKLIST[text] -= 0.5
        if self.BLACKLIST[text] < 0.01:
            del self.BLACKLIST[text]
        self.saveBlacklist()
        return text + ' badness: ' + str(self.BLACKLIST.get(text, 0))

    def addBadness(self, text):
        text = text.strip()
        if not text:
            return 'no action'
        text = text.lower()
        self.BLACKLIST[text] = self.BLACKLIST.get(text, 0.0) + 0.5
        self.saveBlacklist()
        return text + ' badness: ' + str(self.BLACKLIST[text])

    def setBadness(self, text, weight):
        text = text.strip()
        if not text:
            return 'no action'
        text = text.lower()
        self.BLACKLIST[text] = weight
        if weight == 0:
            del self.BLACKLIST[text]
        self.saveBlacklist()
        return text + ' badness: ' + str(self.BLACKLIST.get(text, 0))

    def badTextScore(self, text):
        if matchKey(text, self.WHITELIST):
            return 0, []
        if not text:
            return 0, []
        result = {}
        for x in list(self.BLACKLIST.keys()) + list(self.KICKLIST):
            if x.lower() in text.lower():
                result[x] = self.BLACKLIST.get(x, 1)
        return sum(result.values()), result

    def badText(self, text):
        score, result = self.badTextScore(text)
        if score < 1:
            return
        return ' '.join(result.keys())

    def shouldKick(self, user):
        if len(user.first_name or '') + len(user.last_name or '') > 80:
            return True
        return self.badText(getDisplayUser(user))

    def shouldLog(self, msg):
        if self.shouldDelete(msg)[0] == float('Inf'):
            # good msg
            return False
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.MUTELIST):
            return False
        if msg.forward_from or msg.forward_date or not msg.text:
            return False
        if cnWordCount(msg.text) < 10 or self.badTextScore(msg.text)[0] > 2:
            return False
        if self.badText(msg.text):
            detail = ''
            if len(msg.text) < 40:
                detail = ' msg: ' + msg.text
            return 'text contain: ' + self.badText(msg.text) + detail
        return False # user name not set

    def shouldDeleteReasons(self, msg):
        if not msg.text:
            yield (5, None) # shouldn't be here

        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.MUTELIST):
            yield (5, '非常抱歉，机器人暂时无法判定您的消息，已转交人工审核。')

        score, result = self.badTextScore(msg.text)
        if score >= 1: # may need revisit
            timeout = max(0, 7.5 / (2 ** score - 1) - 2.5) # 拍脑袋
            yield (timeout, default_reason)
        if score > 0:
            yield (60, None)

        if mediumRiskUsr(msg.from_user):
            yield (20, '请先设置用户名再发言，麻烦您啦~ 我们将在20分钟后删除您这条发言，请注意保存。')
        if cnWordCount(msg.text) < 6:
            yield (60, None)

        yield (float('Inf'), None)

    def shouldDelete(self, msg):
        name = getDisplayUser(msg.from_user)
        if matchKey(name, self.WHITELIST):
            return float('Inf'), None

        # delete immediately
        if highRiskUsr(msg.from_user):
            return 0, default_reason
        if msg.photo or msg.sticker or msg.video or msg.document:
            return 0, '您暂时不可以发多媒体信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if msg.forward_from or msg.forward_date:
            return 0, '您暂时不可以转发信息哦~ 已转交人工审核，审核通过会赋予您权限。'
        if cnWordCount(msg.text) < 2:
            return 0, default_reason

        return sorted(list(self.shouldDeleteReasons(msg)))[0]

    def getPermission(self, target):
        tid = str(target.id)
        for l in self.lists:
            if tid in getattr(self, l):
                return l[0].lower()

    def record(self, mlist, target):
        tid = str(target.id)
        for l in self.lists:
            if l == mlist:
                getattr(self, l).add(tid)
            else:
                getattr(self, l).discard(tid)
            self.saveFile(l)
        commit()