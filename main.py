#!/usr/bin/env python3
# coding: utf-8

import functions
import config
import email
from email.header import decode_header
import sys
import asyncio
import traceback


ENCODING = config.encoding


def main():
    imap = functions.connection(config.username, config.mail_pass, config.imap_server)
    if not imap:
        sys.exit()

    status, messages = imap.select("INBOX")  # папка входящие
    res, unseen_msg = imap.uid("search", "UNSEEN", "ALL")
    unseen_msg = unseen_msg[0].decode(ENCODING).split(" ")

    if unseen_msg[0]:
        for letter in unseen_msg:
            attachments = []
            res, message = imap.uid("fetch", letter, "(RFC822)")
            if res == "OK":
                message = email.message_from_bytes(message[0][1])
                msg_date = functions.date_parse(email.utils.parsedate_tz(message["Date"]))
                msg_from = functions.from_subj_decode(message["From"])
                msg_subj = functions.from_subj_decode(message["Subject"])
                if message["Message-ID"]:
                    msg_id = message["Message-ID"].lstrip("<").rstrip(">")
                else:
                    msg_id = message["Received"]
                if message["Return-path"]:
                    msg_email = message["Return-path"].lstrip("<").rstrip(">")
                else:
                    msg_email = msg_from

                if not msg_email:
                    encoding = decode_header(message["From"])[0][1]  # не проверено
                    msg_email = (
                        decode_header(message["From"])[1][0]
                        .decode(encoding)
                        .replace("<", "")
                        .replace(">", "")
                        .replace(" ", "")
                    )

                letter_text = functions.get_letter_text(message)
                attachments = functions.get_attachments(message)

                post_text = functions.post_construct(
                    msg_subj, msg_from, msg_email, letter_text, attachments
                )
                if len(post_text) > 4000:
                    post_text = post_text[:4000]

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                reply_id = loop.run_until_complete(
                    functions.tg_send_message(config.bot_token, post_text, config.chat_id)
                )
                if config.send_attach:
                    functions.get_send_attach(message, msg_subj, reply_id, config.bot_token, config.chat_id)
        imap.logout()
    else:
        imap.logout()
        sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as exp:
        text = str("ошибка: " + str(exp))
        print(traceback.format_exc())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            asyncio.run(functions.tg_send_message(config.bot_token, text, config.chat_id))
        except KeyboardInterrupt:
            pass
