# emailtasker

Restart command line programs via email.

## Installation

1) Download or clone this repository.

2) Run the installation script.
This is very early and quite hacky. I would recommend installing with command:
```bash
python setup.py develop
```

Otherwise you can install normally with:
```bash
python setup.py install
```

## Example
After installation you should have the `emailtasker` script available. You can run it after configuring the `GMAIL_USERNAME` and `GMAIL_PASS` environment variables on your machine. Likewise you can also edit the `test.ini` file with your environment variables containing the email and password data. If you are not using gmail then you will need to configure the `test.ini` file for your email service.


Also recommended is that your navigate to the test folder and run `python fail_script.py` to see what should happen.


If all works as expected, you should start to see emails coming from the configured email account.

## `emailtasker` command line script basics

```bash
$ emailtasker --help
usage: emailtasker [-h] -c CONFIG [-v VERBOSE]

Start a program locally and restart it remotely via email if it crashes.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        A python configuration file (.ini) with the following fields/format:




                                [admin]
                                email_user_envkey: the environment variable storing the user's email address
                                email_pass_envkey: the environment variable storing the user's email password
                                mailbox: the name of the mailbox for the associated address to monitor
                                smtp_server: the smtp server to send emails through
                                smtp_port: the port to connect to the smtp imap_server
                                imap_server: the imap server to monitor
                                imap_port: the port to connect to the imap server over



                                [task]
                                taskname: a name for the task
                                command: the command line program and arguments to execute
                                tasktag: a tag associated with your task. it may make it easier to autofilter emailtasker related emails on your email account
                                log_file_name: the name of a file to log program output to



                                [monitor]
                                restart_kw: keyword in reply emails to restart the task
                                exit_kw: keyword in reply emails to stop runnning the task
                                sleep: time in seconds to wait before rechecking email inbox
                                timeout: time in seconds before the task will automatically exit and the user can no longer restart the program
  -v VERBOSE, --verbose VERBOSE
                        Increased output on user console. May be helpful in debugging.

```
## License
Released under the MIT license.

Copyright 2018 Matthew Antalek Jr

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
