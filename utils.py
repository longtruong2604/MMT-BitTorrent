import socket
import random
import warnings
import os
from datetime import datetime
from configs import CFG, Config
config = Config.from_json(CFG)

# global variables
used_ports = []

def set_socket(ip: str, port: int) -> socket.socket:
    '''
    This function creates a new UDP socket

    :param port: port number
    :return: A socket object with an unused port number
    '''
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, port))
    used_ports.append(port)

    return sock

def free_socket(sock: socket.socket):
    '''
    This function free a socket to be able to be used by others

    :param sock: socket
    :return:
    '''
    used_ports.remove(sock.getsockname()[1])
    sock.close()

def generate_random_port() -> int:
    '''
    This function generates a new(unused) random port number

    :return: a random integer in range of [1024, 65535]
    '''
    available_ports = config.constants.AVAILABLE_PORTS_RANGE
    rand_port = random.randint(available_ports[0], available_ports[1])
    while rand_port in used_ports:
        rand_port = random.randint(available_ports[0], available_ports[1])

    return rand_port

def parse_command(command: str):
    '''
    This function parses the input command

    :param command: A string which is the input command.
    :return: Command parts (mode, filename)
    '''
    parts = command.split(' ')
    try:
        if len(parts) == 2:
            mode = parts[0]
            filename = parts[1]
            return mode, filename
        elif len(parts) == 1:
            mode = parts[0]
            filename = ""
            return mode, filename
    except IndexError:
        warnings.warn("INVALID COMMAND ENTERED. TRY ANOTHER!")
        return

def log(peer_id: int, content: str, is_tracker=False) -> None:
    '''
    This function is used for logging

    :param peer_id: Since each peer has an individual log file to be written in
    :param content: content to be written
    :return:
    '''
    if not os.path.exists(config.directory.logs_dir):
        os.makedirs(config.directory.logs_dir)

    # time
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    content = f"[{current_time}]  {content}\n"
    print(content)

    if is_tracker:
        peer_logs_filename = config.directory.logs_dir + '_tracker.log'
    else:
        peer_logs_filename = config.directory.logs_dir + 'peer' + str(peer_id) + '.log'
    if not os.path.exists(peer_logs_filename):
        with open(peer_logs_filename, 'w') as f:
            f.write(content)
            f.close()
    else:
        with open(peer_logs_filename, 'a') as f:
            f.write(content)
            f.close()




