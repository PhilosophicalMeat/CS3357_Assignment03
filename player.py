import socket
import selectors
import signal
import sys
import argparse
from urllib.parse import urlparse

# Constant list used for checking if a movement command was called
DIRECTIONS = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'UP', 'DOWN']
# Socket for sending messages.

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Server address.

server = ('', '')

# User name for player.

name = ''

# Inventory of items.

inventory = []

# Selector setup
client_selector = selectors.DefaultSelector()

# Command word for use in processing server messages
in_command = ""

# Signal handler for graceful exiting.  Let the server know when we're gone.

def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    message = 'exit'
    client_socket.sendto(message.encode(), server)
    for item in inventory:
        message = f'drop {item}'
        client_socket.sendto(message.encode(), server)
    sys.exit(0)


# Simple function for setting up a prompt for the user.

def do_prompt(skip_line=False):
    if skip_line:
        print("")
    print("> ", end='', flush=True)
    line = sys.stdin.readline()
    process_command(line)


# Function to join a room.

def join_room():
    global client_socket
    global server
    try:
        client_socket.connect(server)
        message = f'join {name}'
        client_socket.send(message.encode())
        response, addr = client_socket.recvfrom(1024)
        response = response.decode()
        print(response)
    except ConnectionRefusedError:
        print('Error: Host or port is not accepting connections.')
        sys.exit(1)


# Function for receiving data from client socket
def handle_data_from_server(sock, mask):
    message = sock.recv(1024)
    message = message.decode()
    words = str(message.split())

    # For 'take' command response
    if (len(words) == 2) and (words[1] == 'taken'):
        inventory.append(words[0])
    # For 'drop' command response
    if len(words) == 2 and words[1] == 'dropped':
        inventory.remove(words[1])

    print(message)



# Function to handle commands from the user, checking them over and sending to the server as needed.

def process_command(command):
    global client_socket
    # Parse command.

    words = command.split()

    # Check if we are dropping something.  Only let server know if it is in our inventory.

    if words[0] == 'drop':
        if len(words) != 2:
            print("Invalid command")
            return
        elif words[1] not in inventory:
            print(f'You are not holding {words[1]}')
            return

    # Send command to server, if it isn't a local only one.

    if command != 'inventory':
        message = f'{command}'
        client_socket.send(message.encode())
        return
    # Check for particular commands of interest from the user.

    if command == 'exit':
        for item in inventory:
            message = f'drop {item}'
            client_socket.send(message.encode())

        sys.exit(0)
    # elif command == 'look':
    #     response, addr = client_socket.recvfrom(1024)
    #     print(response.decode())
    elif command == 'inventory':
        print("You are holding:")
        if len(inventory) == 0:
            print('  No items')
        else:
            for item in inventory:
                print(f'  {item}')
        return
    # elif words[0] == 'take':
    #     response, addr = client_socket.recv(1024)
    #     print(response.decode())
    #     words = response.decode().split()
    #     if (len(words) == 2) and (words[1] == 'taken'):
    #         inventory.append(words[0])
    # elif words[0] == 'drop':
    #     response, addr = client_socket.recvfrom(1024)
    #     print(response.decode())
    #     inventory.remove(words[1])
    # else:
    #     response, addr = client_socket.recvfrom(1024)
    #     print(response.decode())


# Our main function.

def main():
    global name
    global client_socket
    global client_selector
    global server

    # Register our signal handler for shutting down.

    signal.signal(signal.SIGINT, signal_handler)

    # Check command line arguments to retrieve a URL.
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="name for the player in the game")
    parser.add_argument("server", help="URL indicating server location in form of room://host:port")
    args = parser.parse_args()

    # Check the URL passed in and make sure it's valid.  If so, keep track of
    # things for later.

    try:
        server_address = urlparse(args.server)
        if (server_address.scheme != 'room') or (server_address.port is None) or (server_address.hostname is None):
            raise ValueError
        host = server_address.hostname
        port = server_address.port
        server = (host, port)
    except ValueError:
        print('Error:  Invalid server.  Enter a URL of the form:  room://host:port')
        sys.exit(1)
    name = args.name

    # Connect to room, send message to verify

    join_room()

    # Complete what remains of client setup, register inputs from client socket and keyboard

    client_socket.setblocking(False)
    client_selector.register(client_socket, selectors.EVENT_READ, handle_data_from_server)
    client_selector.register(sys.stdin, selectors.EVENT_READ, do_prompt)
    # We now loop forever, sending commands to the server and reporting results

    do_prompt()
    while True:
        events = client_selector.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
    client_selector.close()
if __name__ == '__main__':
    main()
