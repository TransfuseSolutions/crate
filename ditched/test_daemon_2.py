#!/usr/bin/env python

"""
python-daemon
- https://pypi.python.org/pypi/python-daemon/
- https://www.python.org/dev/peps/pep-3143/
- http://stackoverflow.com/questions/4637420/efficient-python-daemon
- http://www.gavinj.net/2012/06/building-python-daemon-process.html
- http://stackoverflow.com/questions/30408589/how-do-you-use-python-daemon-the-way-that-its-documentation-dictates  # noqa

Note that:
- failures are silent
- success is also silent
- the daemon process appears as (e.g.) "python3 ./test_daemon_2.py" in "ps".
"""

import os
try:
    import grp  # UNIX-specific
except ImportError:
    grp = None
import signal
import time
import lockfile

import daemon  # pip install python-daemon



def minimal_test_daemon():
    while True:
        with open("/tmp/current_time.txt", "w") as f:
            f.write("The time is now " + time.ctime() + "\n")
        time.sleep(5)


def main():
    # important_file = open('spam.data', 'w')
    # interesting_file = open('eggs.data', 'w')
    context = daemon.DaemonContext(
        # working_directory='/',
        # umask=0o002,
        # pidfile=lockfile.FileLock('/var/run/spam.pid'),
        # signal_map={
        #     signal.SIGTERM: program_cleanup,
        #     signal.SIGHUP: 'terminate',
        #     signal.SIGUSR1: reload_program_config,
        # },
        # gid=grp.getgrnam('mail').gr_gid,
        # files_preserve=[important_file, interesting_file],
    )

    # initial_program_setup()
    with context:
        minimal_test_daemon()


if __name__ == '__main__':
    main()
