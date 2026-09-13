#!/usr/bin/env python3
"""bionic has no pthread_cancel. Mesa's VK_KHR_display WSI (wsi_common_display.c) stops its wait and
hotplug threads with it, so it will not build for Android. Do what Termux's 0006 does: stop those
threads with a SIGUSR2 handler that pthread_exits, and drop the (meaningless) cancel-type calls.
Written against exact source text rather than diff context so it survives Mesa line drift.

Usage: no_pthread_cancel.py <path to src/vulkan/wsi/wsi_common_display.c>
"""
import sys

path = sys.argv[1]
s = open(path).read()

helper = '''#include <poll.h>
#include <signal.h>

/* bionic has no pthread_cancel: stop a thread by signalling it and exiting from the handler. */
static void
wsi_display_thread_exit_handler(int signum)
{
   pthread_exit(0);
}

static void
wsi_display_cancel_thread(pthread_t thread)
{
   struct sigaction sa;
   memset(&sa, 0, sizeof(sa));
   sigemptyset(&sa.sa_mask);
   sa.sa_handler = wsi_display_thread_exit_handler;
   sigaction(SIGUSR2, &sa, NULL);
   pthread_kill(thread, SIGUSR2);
}
'''
assert s.count('#include <poll.h>\n') == 1, "poll.h include not found once"
s = s.replace('#include <poll.h>\n', helper, 1)

n = s.count('   pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);\n')
assert n == 2, "expected two pthread_setcanceltype calls, found %d" % n
s = s.replace('   pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);\n',
              '   /* no pthread_setcanceltype on bionic: threads are stopped with SIGUSR2 */\n')

for old in ('pthread_cancel(wsi->wait_thread);', 'pthread_cancel(wsi->hotplug_thread);'):
    assert s.count(old) == 1, "expected one " + old
    s = s.replace(old, old.replace('pthread_cancel(', 'wsi_display_cancel_thread('), 1)

assert 'pthread_cancel(' not in s and 'pthread_setcanceltype(' not in s
open(path, 'w').write(s)
print("wsi_common_display.c: pthread_cancel replaced with a SIGUSR2 exit handler")
