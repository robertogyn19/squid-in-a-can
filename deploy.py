#!/usr/bin/env python

# Copyright (c) 2014, Tully Foote

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import os
import subprocess
import socket
import sys
import time

build_cmd = "squid3 -z"
squid_cmd = "squid3 -N"
redirect_cmd = "iptables -t nat -A PREROUTING -p tcp" \
               " --dport 80 -j REDIRECT --to 3129 -w"
remove_redirect_cmd = redirect_cmd.replace(' -A ', ' -D ')

LOCAL_PORT = 3128


def is_port_open(port_num):
    """ Detect if a port is open on localhost"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return sock.connect_ex(('127.0.0.1', port_num)) == 0


class RedirectContext:
    """ A context to make sure that the iptables rules are removed
    after they are inserted."""
    def __enter__(self):
        print("Enabling IPtables forwarding: '%s'" % redirect_cmd)
        subprocess.check_call(redirect_cmd.split())
        return self

    def __exit__(self, type, value, traceback):
        print("Disabling IPtables forwarding: '%s'" % remove_redirect_cmd)
        subprocess.check_call(remove_redirect_cmd.split())


def main():
    if os.geteuid() != 0:
        print("This must be run as root, aborting")
        return -1

    max_object_size = os.getenv("MAXIMUM_CACHE_OBJECT", '1024')
    disk_cache_size = os.getenv("DISK_CACHE_SIZE", '5000')

    print("Setting MAXIMUM_OBJECT_SIZE %s" % max_object_size)
    print("Setting DISK_CACHE_SIZE %s" % disk_cache_size)

    with open("/etc/squid3/squid.conf", 'a') as conf_fh:
        conf_fh.write('maximum_object_size %s MB\n' % max_object_size)
        conf_fh.write('cache_dir ufs /var/cache/squid3 %s 16 256\n' %
                      disk_cache_size)

    # Setup squid directories
    subprocess.check_call(build_cmd, shell=True)

    # wait for the above non-blockin call to finish setting up the directories
    time.sleep(2)

    # Start the squid instance as a subprocess
    squid_in_a_can = subprocess.Popen(squid_cmd, shell=True)

    # While the process is running wait for squid to be running
    while squid_in_a_can.poll() is None and not is_port_open(LOCAL_PORT):
        print("Waiting for port %s to open" % LOCAL_PORT)
        time.sleep(1)

    if is_port_open(LOCAL_PORT):
        print("Port %s detected open setting up IPTables redirection" %
              LOCAL_PORT)
        with RedirectContext():
            # Wait for the squid instance to end or a ctrl-c
            try:
                while squid_in_a_can.poll() is None and \
                        is_port_open(LOCAL_PORT):
                    time.sleep(1)
            except KeyboardInterrupt as ex:
                # Catch Ctrl-C and pass it into the squid instance
                print("CTRL-C caught, shutting down.")
                squid_in_a_can.terminate()

    else:
        print("Port %s never opened, squid instance"
              " must have terminated prematurely" % LOCAL_PORT)

    squid_in_a_can.poll()
    print("Squid process exited with return code %s" %
          squid_in_a_can.returncode)
    return squid_in_a_can.returncode

if __name__ == '__main__':
    sys.exit(main())
