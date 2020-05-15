#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
from telegram import ChatPermissions
from telegram_util import getDisplayUser, log_on_fail, TimedDeleter, matchKey
import yaml
from db import DB, GroupSetting

td = TimedDeleter()

with open('credentials') as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)

updater = Updater(credentials['token'], use_context=True)
tele = updater.bot
debug_group = tele.get_chat(420074357)
db = DB()
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
		if admin.user.id == msg.from_user.id and (admin.can_delete_messages or not admin.can_be_edited):
			return True
	return False

def containBotOwnerAsAdmin(msg):
	for admin in tele.get_chat_administrators(msg.chat_id):
		if admin.user.id == BOT_OWNER:
			return True
	return False

@log_on_fail(debug_group)
def handleGroupInternal(msg):
	global chats
	if not msg.chat.id in chats:
		chats.add(msg.chat.id)
		handleAutoUnblock(chat = [msg.chat.id])
	if db.shouldKick(msg.from_user):
		kick(msg, msg.from_user)
		td.delete(msg, 0)
		return
	if isAdminMsg(msg):
		return

	timeout, reason = db.shouldDelete(msg)
	if timeout != float('Inf'):
		if reason:
			replyText(msg, reason, 1)
		td.delete(msg, timeout)

	log_reason = db.shouldLog(msg)
	if log_reason and containBotOwnerAsAdmin(msg):
		recordDelete(msg, debug_group, tele, 
			db.getPermission(msg.from_user), log_reason)

def handleCommand(msg):
	if not msg.text or len(msg.text.split()) < 2:
		return
	command = msg.text.split()[0].lower()
	text = msg.text.split()[1]
	if not text:
		return
	if command in ['rb', 'reducebadness']:
		r = db.reduceBadness(text)
		msg.chat.send_message(r)
	if command in ['ab', 'addbadness']:
		r = db.addBadness(text)
		msg.chat.send_message(r)
	if command in ['sb', 'setbadness']:
		r = db.setBadness(text, float(msg.text.split()[2]))
		msg.chat.send_message(r)
	if command in ['md', 'moderator_debug']:
		r = db.badText(msg.text)
		msg.chat.send_message('result: ' + str(r))

def handleWildAdminInternal(msg):
	if matchKey(msg.text, ['enable_moderation', 'em']):
		gs.setDisableModeration(msg.chat_id, False)
		return 'moderation enabled'
	if matchKey(msg.text, ['disable_moderation', 'dm']):
		gs.setDisableModeration(msg.chat_id, True)
		return 'moderation disabled'
	if matchKey(msg.text, ['set_greeting', 'sg']):
		if msg.text.find(' ') != -1:
			greeting = msg.text[msg.text.find(' '):].strip()
		else:
			greeting = ''
		gs.setGreeting(msg.chat_id, greeting)
		return 'greeting set to: ' + greeting

def handleWildAdmin(msg):
	r = handleWildAdminInternal(msg)
	if r:
		td.delete(msg.reply_text(r), 0.1)
		msg.delete()

@log_on_fail(debug_group)
def handleGroup(update, context):
	msg = update.effective_message
	if not msg:
		return

	if msg.chat_id != debug_group.id and \
		not gs.isModerationDisabled(msg.chat_id):
		handleGroupInternal(msg)

	if msg.text and msg.text.startswith('/m') and isAdminMsg(msg):
		handleWildAdmin(msg)

	if msg.from_user.id == BOT_OWNER:
		handleAdmin(msg)

@log_on_fail(debug_group)
def handleJoin(update, context):
	msg = update.message
	setting = gs.get(msg.chat_id)
	kicked = False
	for member in msg.new_chat_members:
		if db.shouldKick(member, setting):
			td.delete(msg, 0)
			kicked = True
			kick(msg, member)
	if not kicked:
		td.delete(msg, 5)
		greeting = gs.getGreeting(msg.chat_id)
		if greeting:
			replyText(msg, greeting, 5)

def deleteMsgHandle(update, context):
	msg = update.message
	if gs.get(msg.chat_id).delete_join_left:
		update.message.delete()

@log_on_fail(debug_group)
def handlePrivate(update, context):
	update.message.reply_text('''
Please add me to your group and grant "ban" and "delete" permission.

Possible Commands:
kick_if_name_contains_status - show the blacklist for username
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
kick_if_name_longer_than_status - show status for kick_if_name_longer_than
''')

dp = updater.dispatcher
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handleJoin), group=1)
dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, handleDelete), group = 2)
dp.add_handler(MessageHandler(Filters.group & Filters.command, handleGroup), group = 3)
dp.add_handler(MessageHandler(Filters.private, handlePrivate), group = 4)

updater.start_polling()
updater.idle()