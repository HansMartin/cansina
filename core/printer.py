import os
import sys
import time

try:
    import urlparse
except:
    import urllib.parse as urlparse

if os.name == 'nt':
    RED,MAGENTA,BLUE,GREEN,YELLOW,LBLUE,ENDC = ("","","","","","","")
else:
    RED = '\033[31m'
    MAGENTA = '\033[35m'
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    LBLUE = '\033[36m'
    ENDC = '\033[0m'

COLUMNS = 80

def _get_terminal_width():
    '''
        Get the terminal width to adjust columns size
    '''
    global COLUMNS
    try:
        # (Slightly modified) http://stackoverflow.com/a/943921/91267
        p = os.popen('stty size', 'r')
        rows, columns = p.read().split()
        p.close()
        COLUMNS = int(columns)
    except:
        pass
_get_terminal_width()

class ETAQueue:

    def __init__(self, size, requests):
        self.size = size
        self.times = []
        self.pending_requests = requests

    def get_eta(self):
        mseconds_in_a_hour = 3600000
        mseconds_in_a_minute = 60000
        mseconds_in_a_second = 1000
        if None in self.times:
            self.times = [0 for time in self.times]
        median = sum(self.times)//len(self.times)
        mseconds = self.pending_requests * median

        (r_hours, hours) = (mseconds % mseconds_in_a_hour, int(mseconds / mseconds_in_a_hour))
        (r_minutes, minutes) = (r_hours % mseconds_in_a_minute, int(r_hours / mseconds_in_a_minute))
        (r_seconds, seconds) = (r_minutes % mseconds_in_a_second, int(r_minutes / mseconds_in_a_second))

        if hours > 99:
            (hours, minutes, seconds) = ('NO','TE','ND')

        return "{0:2}h{1:2}m{2:2}s".format(hours, minutes, seconds)

    def set_time(self, time):
        self.pending_requests -= 1
        if len(self.times) == self.size:
            self.times.pop()
        self.times.append(time)

class Console:
    MIN_COLUMN_SIZE = 55
    eta_queue = None
    eta = "00h00m00s"
    show_full_path = False
    show_content_type = False

    @staticmethod
    def start_eta_queue(size, payload_length):
        Console.eta_queue = ETAQueue(size, payload_length)

    @staticmethod
    def header():
        header = os.linesep + "cod |    size    |  line  | time | err. |" \
            + os.linesep +    "-----------------------------------------" + os.linesep
        sys.stdout.write(header)

    @staticmethod
    def body(task):

        color = MAGENTA
        error_format = color + "{1: ^3} | {2: >10} | {3: >6} | {4: >4} | {8: >4} | {7} [{0: >2}%] - {5: ^9} - {6}" + ENDC

        percentage = int(task.number * 100 / task.get_payload_length())

        target = task.get_complete_target()
        target = urlparse.urlsplit(target).path
        if sys.version_info[0] == 3:
            t_encode = target
        else:
            t_encode = target.encode('utf-8')


        # User wants to see full path
        if Console.show_full_path:
            t_encode = task.get_complete_target()
        else:
            t_encode = target

        # Fix three characters off by one on screen
        if percentage == 100:
            percentage = 99

        Console.eta_queue.set_time(task.response_time)
        if task.number % 10 == 0:
            Console.eta = Console.eta_queue.get_eta()

        # Show or not 'Content-Type'
        if Console.show_content_type:
            content_type = task.response_type + " |"
        else:
            content_type = ""

        # If a task is valid means that is should be printed, so a proper
        # linesep will be printed
        linesep = ""
        if task.is_valid():
            linesep = os.linesep
        elif os.name == 'nt':
            return

        if task.location:
            target = target + " -> " + task.location
        if len(target) > COLUMNS - Console.MIN_COLUMN_SIZE:
            target = target[:abs(COLUMNS - Console.MIN_COLUMN_SIZE)]



        if task.error_occured:
            linesep = ""
            to_console = error_format.format(percentage, 0,
                                          0, task.number,
                                          0,
                                          Console.eta,
                                          t_encode, content_type, task.num_errors)
            sys.stdout.write(to_console[:COLUMNS-2] + linesep)
            sys.stdout.flush()
            sys.stdout.write('\r')
            if not os.name == 'nt':
                sys.stdout.write("\x1b[0K")
            return




        color = ""
        if task.response_code == "200":
            color = GREEN
        if task.response_code == "401" or task.response_code == "403":
            color = RED
        if task.response_code == "301" or task.response_code == "302":
            color = LBLUE
        if task.response_code.startswith('5') or task.response_code == '400':
            color = YELLOW
        if task.content_detected:
            color = MAGENTA

        to_format = color + "{1: ^3} | {2: >10} | {3: >6} | {4: >4} | {8: >4} | {7} [{0: >2}%] - {5: ^9} - {6}" + ENDC
        to_format_without_progress = color + "{0: ^3} | {1: >10} | {2: >6} | {3: >4} | {4: >4} | {5:^} {4}" + ENDC


        # if an entry is about to be log, remove percentage and eta time
        if color:
            to_console = to_format_without_progress.format(task.response_code,
                                                    task.response_size,
                                                    task.number,
                                                    int(task.response_time),
                                                    task.num_errors,
                                                    t_encode, content_type)
        # print with progress
        else:
            to_console = to_format.format(percentage, task.response_code,
                                          task.response_size, task.number,
                                          int(task.response_time),
                                          Console.eta,
                                          t_encode, content_type, task.num_errors)

        sys.stdout.write(to_console[:COLUMNS-2] + linesep)
        sys.stdout.flush()
        sys.stdout.write('\r')

        if not os.name == 'nt':
            sys.stdout.write("\x1b[0K")

