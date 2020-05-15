#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
from telegram_util import log_on_fail, TimedDeleter, matchKey
import yaml
from group_setting import GroupSetting

td = TimedDeleter()

with open('credentials') as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(credentials['token'], use_context=True)
tele = updater.bot
debug_group = tele.get_chat(420074357)
gs = GroupSetting()

def replyText(msg, text, timeout):
	try:
		return td.delete(msg.reply_text(text), timeout)
	except:
		pass

def kick(msg, member):
	try:
		for _ in range(2):
			tele.kick_chat_member(msg.chat.id, member.id)
	except Exception as e:
		pass

def isAdminMsg(msg):
	for admin in tele.get_chat_administrators(msg.chat_id):
		if admin.user.id == msg.from_user.id:
			return True
	return False

commands_detail = '''kick_if_name_contains_status - show the blacklist for username
kick_if_name_contains_add - add word to username blacklist
kick_if_name_contains_remove - remove word from username blacklist
delete_if_message_is_forward_on - delete if message is forward
delete_if_message_is_forward_off - turn off delete_if_message_is_forward
delete_if_message_is_forward_status - show status for delete_if_message_is_forward
delete_join_left_message_on - delete join left message
delete_join_left_message_off - turn off delete_join_left_message
delete_join_left_message_status - show status for delete_join_left_message
welcome_message_off - turn off welcome message
welcome_message_set - set welcome message
welcome_message_status - show welcome message 
warning_on_message_delete_off - hide warning when bot delete user's message
warning_on_message_delete_set - set warning message when bot delete user's message
warning_on_message_delete_status - show the current warning message when bot delete user's message
kick_if_name_longer_than_off - turn off kick_if_name_longer_than
kick_if_name_longer_than_set - kick if name longer than how many characters
kick_if_name_longer_than_status - show status for kick_if_name_longer_than'''

commands = [x.split(' - ')[0] for x in commands_detail.split('\n')]

@log_on_fail(debug_group)
def handleGroupCommand(update, context):
	msg = update.message
	if not matchKey(msg.text, commands):
		return

	if not isAdminMsg(msg):
		td.delete(msg, 0)
		return

	setting = gs.get(msg.chat_id)
	r = setting.update(msg.text)
	replyText(msg, r, 0.1)
	td.delete(msg, 0)

@log_on_fail(debug_group)
def handleGroupForward(update, context):
	msg = update.message
	setting = gs.get(msg.chat_id)
	if not setting.delete_if_message_is_forward:
		return
	if isAdminMsg(msg):
		return
	if setting.warning_on_message_delete:
		replyText(msg, setting.warning_on_message_delete, 5)
	td.delete(msg, 0)

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	setting = gs.get(msg.chat_id)
	
	kicked = False
	for member in msg.new_chat_members:
		if setting.shouldKick(member):
			td.delete(msg, 0)
			kicked = True
			kick(msg, member)
	if kicked:
		return

	if setting.delete_join_left:
		td.delete(msg, 5)

	if setting.greeting:
		replyText(msg, setting.greeting, 5)

def handleDelete(update, context):
	msg = update.message
	if gs.get(msg.chat_id).delete_join_left:
		update.message.delete()

@log_on_fail(debug_group)
def handlePrivate(update, context):
	# testing
	raise Exception('123')
	update.message.reply_text('''
Please add me to your group and grant "ban" and "delete" permission.

Possible Commands:
''' + commands_detail)

dp = updater.dispatcher
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, handleDelete), group = 2)
dp.add_handler(MessageHandler(Filters.group & Filters.command, handleGroupCommand), group = 3)
dp.add_handler(MessageHandler(Filters.group & Filters.forwarded, handleGroupForward), group = 4)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 5)

updater.start_polling()
updater.idle()