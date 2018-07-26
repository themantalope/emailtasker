import os
import sys
import configparser
import shlex
import smtplib
import imaplib
import subprocess
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from email.utils import make_msgid
import datetime
import collections
import time




class Tasker(object):

    def __init__(self,
                task_config_file,
                email_user_pass_func=None,
                email_user_pass_args=None,
                verbose=False):
        self.task_config_file = task_config_file
        self.verbose = verbose
        self.config = configparser.ConfigParser()
        self.config.read(self.task_config_file, encoding=None)
        # check to make sure there is an admin section
        assert "admin" in self.config,"config file needs an 'admin' section!"
        # check to make sure there is a task section
        assert "task" in self.config,"config file needs a 'task' section"
        # check to make sure there is a monitor section
        assert "monitor" in self.config,"config file needs a 'monitor' section"
        self.ready = False
        self.parse_task()
        self.log_file_name = self.config['task']['log_file_name']
        self.task_email_subject = None # update this once we have a PID
        self.last_sent_message_id = None
        self.last_received_reply_id = None
        if "sleep" in self.config['monitor']:
            self.sleep_time = float(self.config['monitor']['sleep'])
        else:
            self.sleep_time = float(5)
        if ("email_user_envkey" not in self.config['admin']) or\
           ("email_pass_envkey" not in self.config['admin']):
            email_user, email_pass = email_user_pass_func(*email_user_pass_args)
            self.email_addr = email_user
            self.email_pass = email_pass
        else:
            self.email_addr = os.environ[self.config['admin']['email_user_envkey']]
            self.email_pass = os.environ[self.config['admin']['email_pass_envkey']]




    def run(self):
        assert self.ready, "You need to parse the task before running."
        # start running the task
        if self.verbose:
            with open(self.task_config_file, "r") as fp:
                configdata = fp.read()
            print("Running task '{tn}'.".format(tn=self.config['task']['taskname']))
            print("\n\n")
            print("Config file contents: ")
            print(configdata)
            print("Task output:\n\n")

        while True:
            with open(self.log_file_name, mode='w') as logf:
                self.process = subprocess.Popen(self.command,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
                self.task_email_subject = self.config['task']['tasktag'] + " '{tn}' with pid {p}".format(tn=self.config['task']['taskname'],
                                                                                                         p=self.process.pid)
                # send an email notifying the admin that a task is starting
                self.send_start_message()
                while self.process.poll() is None:
                    stdoutline = self.process.stdout.readline().decode("utf-8")
                    while stdoutline != "":
                        logf.write(stdoutline)
                        if self.verbose:
                            print(stdoutline)
                            sys.stdout.flush()
                        stdoutline = self.process.stdout.readline().decode("utf-8")

                # if we're here it means that "poll" returned a value
                logf.write("\n")
                logf.write("ERRORS:\n")
                errors = self.process.stderr.read().decode("utf-8")
                logf.write(self.process.stderr.read().decode("utf-8"))
                logf.write("\n")
                logf.write("End time: {t}".format(t=str(datetime.datetime.now())))
                if self.verbose:
                    print(errors)
                # finish writing the log file
            # send an email saying the task is done and ask if what they want
            # to do
            if self.verbose:
                print("\n\nTask has ended.")
                print("Sending task end message.")
            self.send_task_end_message()
            if self.verbose:
                print("Waiting for user response.")
            user_response = self.get_admin_response()
            if user_response == self.config['monitor']['exit_kw']:
                print("Exiting '{tn}''!".format(tn=self.config['task']['taskname']))
                print("Thanks for using emailtasker!")
                self.send_exit_email()
                break
            elif user_response == self.config['monitor']['restart_kw']:
                print("Restarting '{tn}'. You should receive an email shortly for a new task with a new PID.".format(tn=self.config['task']['taskname']))
                self.send_restart_email()
                continue

        return


    def send_exit_email(self):
        message_bod = "You have chosen to exit task '{tn}'' with pid {pid}.".format(tn=self.config['task']['taskname'],
                                                                                 pid=self.process.pid)
        message_bod += "\n\nThanks for using emailtakser! Bye!"
        subject = "Re: " + self.task_email_subject
        message_final = self._format_message(self.email_addr,
                                             subject,
                                             message_body=message_bod,
                                             in_reply_to=self.last_received_reply_id)

        self._smtp_send(self.email_addr, self.email_addr, message_final)
        return

    def send_restart_email(self):
        message_bod = "You have chosen to restart task '{tn}'' with pid {pid}.".format(tn=self.config['task']['taskname'],
                                                                                 pid=self.process.pid)
        message_bod += "\nYou should receive an email shortly for your new task and PID."
        message_bod += "\n\nThanks for using emailtakser! Bye!"
        subject = "Re: " + self.task_email_subject
        message_final = self._format_message(self.email_addr,
                                             subject,
                                             message_body=message_bod,
                                             in_reply_to=self.last_received_reply_id)
        self._smtp_send(self.email_addr, self.email_addr, message_final)
        return

    def get_admin_response(self):

        self._imap_login()
        rv, _ = self.imap.select(self.config['admin']['mailbox'])
        #print("first select: ", _)
        assert rv=='OK',"Could not select mailbox: {mb}".format(mb=self.config['admin']['mailbox'])
        start = datetime.datetime.now()
        wait = float(self.config['monitor']['timeout']) # timeout in seconds
        respval = None
        while (datetime.datetime.now() - start).total_seconds() < wait:
            # search for a response
            # print("searching mailbox...")
            # print("searching for: ", '"{lid}"'.format(lid=self.last_sent_message_id))
            rv, _ = self.imap.select(self.config['admin']['mailbox'])
            assert rv=='OK',"Could not select mailbox: {mb}".format(mb=self.config['admin']['mailbox'])
            # print("reselect: ", _)
            rv, ids = self.imap.search(None, "HEADER In-Reply-To", '"{lid}"'.format(lid=self.last_sent_message_id))
            # print("rv: ",rv)
            # print("ids: ", ids)
            if len(ids[0].split()) > 0:
                first_id = ids[0].split()[0]
                rv, raw_message = self.imap.fetch(first_id, "(RFC822)")
                received_message = email.message_from_bytes(raw_message[0][1])
                response = received_message.get_payload()[0]
                self.last_received_reply_id = received_message.get("Message-ID")
                # print('last reply id: ', self.last_received_reply_id)
                response_text = response.get_payload()
                response_lines = response_text.split("\n")
                # TODO: Update this so it's less brittle. Will only look at the
                # first line of the response email for the desired action
                response_final = response_lines[0]

                if self.verbose:
                    print("User response: ", response_final)

                restart_in_response = False
                exit_in_response = False
                if self.config['monitor']['restart_kw'] in response_final:
                    restart_in_response = True

                if self.config['monitor']['exit_kw'] in response_final:
                    exit_in_response = True

                if restart_in_response and not exit_in_response:
                    respval = self.config['monitor']['restart_kw']
                elif not restart_in_response and exit_in_response:
                    respval = self.config['monitor']['exit_kw']
                elif restart_in_response and exit_in_response:
                    self.send_clarification_email()
                    if self.verbose:
                        print("Response contains both exit and restart keywords.")
                else:
                    self.send_clarification_email()
                    if self.verbose:
                        print("Response contains neither exit nor restart keywords.")
            if respval is not None:
                break
            else:
                if self.verbose:
                    print("Waiting for user response.")
                    print("Waiting {s} seconds.".format(s=self.sleep_time))
                time.sleep(self.sleep_time)
        return respval

    def send_clarification_email(self):
        message_bod = "Your response for task '{tn}' with pid {pid} either contained neither or both restart and exit keywords.".format(tn=self.config['task']['taskname'],
                                                                                                                                        pid=self.process.pid)
        message_bod += "\n"
        message_bod += "To restart this task reply to this email with: {rs}.".format(rs=self.config['monitor']['restart_kw'])
        message_bod += "\nTo exit reply with: {ex}.".format(ex=self.config['monitor']['exit_kw'])

        subject = "Re: " + self.task_email_subject

        message_final = self._format_message(self.email_addr,
                                             subject=subject,
                                             message_body=message_bod,
                                             in_reply_to=self.last_received_reply_id)

        self._smtp_send(self.email_addr, self.email_addr, message_final)

        return

    def send_task_end_message(self):
        message_bod = "Task '{tn}' with pid {pid} has exited with code {ec}.".format(tn=self.config['task']['taskname'],
                                                                                     pid=self.process.pid,
                                                                                     ec=self.process.poll())
        message_bod += "\nThe logfile has been attached to this email."

        message_bod += '\n\n'
        message_bod += "To restart this task reply to this email with: {rs}.".format(rs=self.config['monitor']['restart_kw'])
        message_bod += "\nTo exit reply with: {ex}.".format(ex=self.config['monitor']['exit_kw'])
        message_bod += "\nThis task will automatically exit in {time} seconds.".format(time=self.config['monitor']['timeout'])

        subject = "Re: " + self.task_email_subject

        message_final = self._format_message(self.email_addr,
                                             subject,
                                             message_body=message_bod,
                                             in_reply_to=self.last_sent_message_id,
                                             attachments=self.log_file_name)

        self._smtp_send(self.email_addr, self.email_addr, message_final)

        return

    def send_start_message(self):
        message_bod = "Starting Task!"
        message_bod += "\ncommand: {cmd}".format(cmd=" ".join(self.command))
        message_bod += "\nprocess id: {pid}".format(pid=self.process.pid)
        message_bod += "\ntime: {t}".format(t=str(datetime.datetime.now()))

        subject = self.task_email_subject

        message_final = self._format_message(self.email_addr, subject, message_body=message_bod)

        self._smtp_send(self.email_addr, self.email_addr, message_final)

        return

    def _smtp_login(self):
        server = smtplib.SMTP(host=self.config['admin']['smtp_server'],
                              port=self.config['admin']['smtp_port'])
        server.starttls()
        server.login(self.email_addr, self.email_pass)
        self.smtp = server
        return

    def _smtp_send(self, to_addr, from_addr, message):
        self._smtp_login()
        assert self.smtp.noop()[0] == 250,"Can't send mail, not logged in."
        self.smtp.sendmail(from_addr, to_addr, message.as_bytes())
        self.smtp.quit() # quit for now, force login at each send
        return

    def _imap_login(self):
        mail = imaplib.IMAP4_SSL(host=self.config['admin']['imap_server'],
                                 port=self.config['admin']['imap_port'])
        mail.login(self.email_addr, self.email_pass)
        self.imap = mail
        return

    def _format_message(self,
                        to_addr,
                        subject,
                        message_body=None,
                        message_body_html=None,
                        in_reply_to=None,
                        attachments=None):

        message = MIMEMultipart("mixed")
        message['Subject'] = subject
        message['From'] = self.email_addr
        message['To'] = to_addr
        mid = make_msgid()
        message['Message-ID'] = mid
        self.last_sent_message_id = mid
        if message_body is not None:
            message.attach(MIMEText(message_body, 'plain'))
            if self.verbose:
                print("Sending message with plaintext body: ")
                print(message_body)
        elif message_body_html is not None:
            message.attach(MIMEText(message_body_html,'html'))
            if self.verbose:
                print("Sending message with HTML body: ")
                print(message_body_html)
        else:
            message.attach(MIMEText("","plain"))
            if self.verbose:
                print("Sending message with plaintext body: ")
                print("")
        if in_reply_to is not None:
            if "re" not in subject.lower():
                message['Subject'] = 'Re: ' + subject
            message['In-Reply-To'] = in_reply_to

        if attachments is not None:
            # print(attachments)
            if not isinstance(attachments, list):
                attachments = [attachments]
            for fn in attachments:
                # print(fn)
                if self.verbose:
                    print("Attaching file: ", fn)
                mime_payload = MIMEBase("application", "octet-stream")
                with open(fn, mode="rb") as fp:
                    mime_payload.set_payload(fp.read())

                encode_base64(mime_payload)
                mime_payload.add_header("Content-Disposition", "attachment",filename=fn)
                message.attach(mime_payload)


        # print(message.get_payload()[0].get_payload())
        if self.verbose:
            print("Sending email with parts: ")
            for k, v in message.items():
                print(k, ": ", v)
        return message

    def parse_task(self):
        command = self.config['task'].get("command")
        self.command = shlex.split(command, comments=False, posix=True)
        self.ready = True
