#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
from telegram_util import log_on_fail, TimedDeleter, matchKey, log
import yaml
from group_setting import GroupSetting
from db import DB

td = TimedDeleter()
db = DB()

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

commands = ['kick_if_name_contains_status',
'kick_if_name_contains_add',
'kick_if_name_contains_remove',
'delete_if_message_is_forward_on',
'delete_if_message_is_forward_off',
'delete_if_message_is_forward_status',
'delete_join_left_message_on',
'delete_join_left_message_off',
'delete_join_left_message_status',
'welcome_message_off',
'welcome_message_set',
'welcome_message_status',
'warning_on_message_delete_off',
'warning_on_message_delete_set',
'warning_on_message_delete_status',
'kick_if_name_longer_than_off',
'kick_if_name_longer_than_set',
'kick_if_name_longer_than_status',]

help_message = '''
Please add me to your group and grant "ban" and "delete" permission.

Possible Commands:
''' + '\n'.join(commands)

@log_on_fail(debug_group)
def handleGroupCommand(update, context):
	msg = update.message
	if not msg or not msg.text:
		return 

	if 'moderator_show_commands' in msg.text:
		replyText(msg, help_message, 5)
		td.delete(msg, 0.1)

	if not matchKey(msg.text, commands):
		return

	if not isAdminMsg(msg):
		td.delete(msg, 0)
		return

	setting = gs.get(msg.chat_id)
	r = setting.update(msg.text)
	if 'status' not in msg.text:
		gs.save()
		replyText(msg, r, 0.1)
	else:
		replyText(msg, r, 5)
	td.delete(msg, 0.1)

@log_on_fail(debug_group)
def handleGroupForward(update, context):
	msg = update.message
	if not msg:
		debug_group.send_message('no message for forward message')
		debug_group.send_message(str(update.effective_message))
		debug_group.send_message(str(update))
		return
	setting = gs.get(msg.chat_id)
	if not setting.delete_if_message_is_forward:
		return
	if isAdminMsg(msg):
		return
	if str(msg.from_user.id) in db.whitelist:
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
	update.message.reply_text(help_message)

dp = updater.dispatcher
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, handleDelete), group = 2)
dp.add_handler(MessageHandler(Filters.group, handleGroupCommand), group = 3)
dp.add_handler(MessageHandler(Filters.group & Filters.forwarded, handleGroupForward), group = 4)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 5)

updater.start_polling()
updater.idle()