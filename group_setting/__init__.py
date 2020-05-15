from telegram_util import matchKey, getDisplayUser, splitCommand
import yaml

# TODO: see if I want to accept command without '/'
# TODO: for blacklist ban, scan through all member

def commit():
    # see if I need to deal with race condition
    command = 'git add . > /dev/null 2>&1 && git commit -m commit > /dev/null 2>&1 && git push -u -f > /dev/null 2>&1'
    threading.Timer(60, lambda: os.system(command)).start()

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

        if 'kick_if_name_longer_than' in command:
            if 'kick_if_name_longer_than_off' in command:
                self.kick_if_name_longer_than = 0
            if 'kick_if_name_longer_than_set' in command:
                try:
                    new_value = int(text)
                except:
                    return 'please give a int'
                if new_value < 20:
                    return 'can not set kick_if_name_longer_than to a value less than 20'
                self.kick_if_name_longer_than = new_value
            if self.kick_if_name_longer_than:
                return 'kick if name longer than %d characters' % self.kick_if_name_longer_than
            else:
                return 'kick_if_name_longer_than not set'

        if 'kick_if_name_contains' in command:
            new_values = [x.strip() for x in text.split() if x.strip()]
            if 'kick_if_name_contains_add' in command:
                self.kick_if_name_contains += new_values
            if 'kick_if_name_contains_remove' in command:
                self.kick_if_name_contains = [x for x in self.kick_if_name_contains 
                    if x not in new_values]
            return 'kick_if_name_contains: ' + str(self.kick_if_name_contains)

class GroupSetting(object):
    def __init__(self):
        self.fn = 'group_setting/SETTING'
        with open(self.fn) as f:
            self.setting = yaml.load(f, Loader=yaml.FullLoader)
        self.setting = {x: Setting(self.setting[x]) for x in self.setting}

    def get(self, chat_id):
        if chat_id not in self.setting:
            self.setting[chat_id] = Setting({})
        return self.setting[chat_id]

    def save(self):
        with open(self.fn, 'w') as f:
            f.write(yaml.dump(self.setting, sort_keys=True, indent=2))
        commit()