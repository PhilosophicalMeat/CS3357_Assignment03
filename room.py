import selectors
import socket
import signal
import sys
import argparse
from urllib.parse import urlparse

# Saved information on the room.

name = ''
description = ''
items = []

# Declaring Selector and boolean for while-loop
serverSel = selectors.DefaultSelector()

keep_running = True

# Room Connection order: NORTH, SOUTH, EAST, WEST, UP, DOWN
# Order of tuple contents: direction, hostname, int(port)
adjacent_rooms = []

# Constant list used for checking if a movement command was called
DIRECTIONS = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'UP', 'DOWN']
# List of clients currently in the room.

client_list = []

# Used for storing connected sockets
connections = []


# Signal handler for graceful exiting.

def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)


# Confirm that movement to another room is possible
def server_get_room(direction):
    global adjacent_rooms
    global DIRECTIONS

    for adjacent_server in adjacent_rooms:
        if adjacent_server[0].upper() == direction.upper():
            return '{} {} {}'.format(adjacent_server[0], adjacent_server[1], adjacent_server[2])
        else:
            if direction.upper() != "UP" and direction.upper() != "DOWN":
                return 'There is no hatch leading {}.'.format(direction)
            else:
                return 'There is no door to the {}.'.format(direction)


# Search the client list for a particular player.

def client_search(player):
    for reg in client_list:
        if reg[0] == player:
            return reg[1]
    return None


# Search the client list for a particular player by their address.

def client_search_by_address(address):
    for reg in client_list:
        if reg[1] == address:
            return reg[0]
    return None


# Add a player to the client list.

def client_add(player, address):
    registration = (player, address)
    client_list.append(registration)


# Remove a client when disconnected.

def client_remove(player):
    for reg in client_list:
        if reg[0] == player:
            client_list.remove(reg)
            break


# Summarize the room into text.

def summarize_room():
    global name
    global description
    global items
    global adjacent_rooms
    global client_list

    # Putting room name and description into a string
    summary = name + '\n\n' + description + '\n'

    # Loop for adding available connections
    for room in adjacent_rooms:
        if room[0] != "":
            # For rooms going in cardinal directions
            if room[0] != "up" or room[0] != "down":
                summary += 'A doorway leads away from the room to the ' + room[0] + '.\n'
            # For rooms going up/ down
            else:
                summary += 'A hatch leads out of the room going ' + room[0] + '.\n'
    summary += '\n'

    # Adding room's items to summary
    if len(items) == 0:
        summary += "The room is empty.\n"
    elif len(items) == 1:
        summary += "In this room, there is:\n"
        summary += f'  {items[0]}\n'
    else:
        summary += "In this room, there are:\n"
        for item in items:
            summary += f'  {item}\n'

    # Returning the completed summary
    return summary


# Function for printing the list of player's in the room
def get_other_players(address):
    summary = ""
    # Adding list of other players/ clients in the room to the summary
    if len(client_list) == 1:
        summary += "There are no other players in this room."
    elif len(client_list) == 2:
        summary += "There is one other player in this room: "
        for client in client_list:
            if client[1] != address:
                summary += '{}.\n'.format(client[0])
    else:
        summary += 'The other players in this room are: \n'
        for client in client_list:
            if client[1] != address:
                summary += '{}\n'.format(client[0])


# Print a room's description.

def print_room_summary():
    print(summarize_room()[:-1])


# Function for accepting new connections
def accept(socket, mask):
    global serverSel
    client_connection, address = socket.accept()
    print("New socket registered from address {}".format(address))
    client_connection.setblocking(False)
    serverSel.register(client_connection, selectors.EVENT_READ, process_message)


# Process incoming message.

def process_message(connection, addr):
    global serverSel
    global connections
    # Parse the message.
    message = connection.recv(1024).decode()
    words = message.split()

    # If player is joining the server, add them to the list of players.

    if (words[0] == 'join'):
        if (len(words) == 2):
            client_add(words[1], addr)
            connections.append(connection)

            print(f'User {words[1]} joined from address {addr}')
            response = 'User {} entered the room.'.format(client_search_by_address(addr))
            for client in connections:
                if client is not connection:
                    client.send(response.encode())
            connection.send(summarize_room()[:-1].encode())
        else:
            connection.send("Invalid command".encode())

    # If player is leaving the server. remove them from the list of players.

    elif (message == 'exit'):
        response = 'User {} has left the server'.format(client_search_by_address(addr))
        client_remove(client_search_by_address(addr))
        connections.remove(connection)
        for client in connections:
            if client is not connection:
                client.send(response.encode())
        connection.send('Goodbye'.encode())
        connection.close()

    # If player looks around, give them the room summary.

    elif (message == 'look'):
        summary = summarize_room()[:-1]
        # Adding client list to summary
        summary += get_other_players(addr)
        connection.send(summary[:-1].encode())

    # If player takes an item, make sure it is here and give it to the player.

    elif (words[0] == 'take'):
        if (len(words) == 2):
            if (words[1] in items):
                items.remove(words[1])
                connection.send(f'{words[1]} taken'.encode())
            else:
                connection.send(f'{words[1]} cannot be taken in this room'.encode())
        else:
            connection.send("Invalid command".encode())

    # If player drops an item, put it in the list of things here.

    elif (words[0] == 'drop'):
        if (len(words) == 2):
            items.append(words[1])

            connection.send(f'{words[1]} dropped'.encode())
        else:
            connection.send("Invalid command".encode())

    # If player says something to rest of server, send to other players
    elif words[0] == 'say':
        msg = '{} said \"{}\"'.format(client_search_by_address(addr), message[4:-1])
        for client in connections:
            if client is not connection:
                client.send(msg.encode())
        response = 'You said \"{}\".'.format(message[4:-1])
        connection.send(response.encode())

    # If player calls to move to one of adjacent rooms, confirm room connection and move player
    elif words[0].upper() in DIRECTIONS:
        msg = server_get_room(words[0])

    # Otherwise, the command is bad

    else:
        connection.send("Invalid command".encode())


# Our main function.

def main():
    global name
    global description
    global items
    global adjacent_rooms

    # Register our signal handler for shutting down.

    signal.signal(signal.SIGINT, signal_handler)

    # Check command line arguments for room settings.
    parser = argparse.ArgumentParser()
    # NEW CODE for parsing optional arguments
    # subparser = parser.add_subparsers()
    # Parsing optional arguments
    parser.add_argument("-s", type=str, nargs=1)
    parser.add_argument("-n", type=str, nargs=1)
    parser.add_argument("-e", type=str, nargs=1)
    parser.add_argument("-w", type=str, nargs=1)
    parser.add_argument("-u", type=str, nargs=1)
    parser.add_argument("-d", type=str, nargs=1)
    # Parsing arguments necessary for server launch
    parser.add_argument("port", type=int, help="port number to list on")
    parser.add_argument("name", help="name of the room")
    parser.add_argument("description", help="description of the room")
    parser.add_argument("item", nargs='*', help="items found in the room by default")
    args = parser.parse_args()
    port = args.port
    name = args.name
    description = args.description
    items = args.item

    # Updating connections list
    if args.n:
        server_addr = urlparse(args.n[0])
        adjacent_rooms.append(("north", str(server_addr.hostname), server_addr.port))
    if args.s:
        server_addr = urlparse(args.s[0])
        adjacent_rooms.append(("south", str(server_addr.hostname), server_addr.port))
    if args.e:
        server_addr = urlparse(args.e[0])
        adjacent_rooms.append(("east", str(server_addr.hostname), server_addr.port))
    if args.w:
        server_addr = urlparse(args.w[0])
        adjacent_rooms.append(("west", str(server_addr.hostname), server_addr.port))
    if args.u:
        server_addr = urlparse(args.u[0])
        adjacent_rooms.append(("up", str(server_addr.hostname), server_addr.port))
    if args.d:
        server_addr = urlparse(args.d[0])
        adjacent_rooms.append(("down", str(server_addr.hostname), server_addr.port))

    # Report initial room state.
    print('Room Starting Description:\n')
    print_room_summary()

    # Create the socket.  We will ask this to work on any interface and to use
    # the port given at the command line.  We'll print this out for clients to use.

    room_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    room_socket.setblocking(False)
    room_socket.bind(('', port))
    room_socket.listen(5)
    print('\nRoom will wait for players at port: ' + str(room_socket.getsockname()[1]))

    # Registering the accept function to selector
    serverSel.register(room_socket, selectors.EVENT_READ, accept)

    # Loop forever waiting for messages from clients.
    while keep_running:
        for key, mask in serverSel.select():
            callback = key.data
            callback(key.fileobj, mask)
    print("Shutting down...")
    serverSel.close()
    # while True:
    #     # Receive a packet from a client and process it.
    #
    #     message, addr = room_socket.recvfrom(1024)
    #
    #     # Process the message and retrieve a response.
    #
    #     response = process_message(message.decode(), addr)
    #
    #     # Send the response message back to the client.
    #
    #     room_socket.sendto(response.encode(), addr)


if __name__ == '__main__':
    main()
