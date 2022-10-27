import socket
import signal
import sys
import argparse

# Saved information on the room.

name = ''
description = ''
items = []
connections = []

# List of clients currently in the room.

client_list = []

# Signal handler for graceful exiting.  

def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)

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

    # Pack description into a string and return it.

    summary = name + '\n\n' + description + '\n\n'
    if len(items) == 0:
        summary += "The room is empty.\n"
    elif len(items) == 1:
        summary += "In this room, there is:\n"
        summary += f'  {items[0]}\n'
    else:
        summary += "In this room, there are:\n"
        for item in items:
            summary += f'  {item}\n'

    return summary

# Print a room's description.

def print_room_summary():

    print(summarize_room()[:-1])

# Process incoming message.

def process_message(message, addr):

    # Parse the message.
 
    words = message.split()

    # If player is joining the server, add them to the list of players.

    if (words[0] == 'join'):
        if (len(words) == 2):
            client_add(words[1],addr)
            print(f'User {words[1]} joined from address {addr}')
            return summarize_room()[:-1]
        else:
            return "Invalid command"

    # If player is leaving the server. remove them from the list of players.

    elif (message == 'exit'):
        client_remove(client_search_by_address(addr))
        return 'Goodbye'

    # If player looks around, give them the room summary.

    elif (message == 'look'):
        return summarize_room()[:-1]
            
    # If player takes an item, make sure it is here and give it to the player.

    elif (words[0] == 'take'):
        if (len(words) == 2):
            if (words[1] in items):
                items.remove(words[1])
                return f'{words[1]} taken'
            else:
                return f'{words[1]} cannot be taken in this room'
        else:
            return "Invalid command"

    # If player drops an item, put in in the list of things here.

    elif (words[0] == 'drop'):
        if (len(words) == 2):
            items.append(words[1])
            return f'{words[1]} dropped'
        else:
            return "Invalid command"

    # Otherwise, the command is bad.

    else:
        return "Invalid command"

# Our main function.

def main():

    global name
    global description
    global items
    global connections

    # Register our signal handler for shutting down.

    signal.signal(signal.SIGINT, signal_handler)

    # Check command line arguments for room settings.

    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="port number to list on")
    parser.add_argument("name", help="name of the room")
    parser.add_argument("description", help="description of the room")
    parser.add_argument("item", nargs='*', help="items found in the room by default")
    args = parser.parse_args()

    port=args.port
    name = args.name
    description = args.description
    items = args.item

    # Report initial room state.
    print('Room Starting Description:\n')
    print_room_summary()

    # Create the socket.  We will ask this to work on any interface and to use
    # the port given at the command line.  We'll print this out for clients to use.

    room_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    room_socket.bind(('', port))
    print('\nRoom will wait for players at port: ' + str(room_socket.getsockname()[1]))

    # Loop forever waiting for messages from clients.

    while True:

        # Receive a packet from a client and process it.

        message, addr = room_socket.recvfrom(1024)

        # Process the message and retrieve a response.

        response = process_message(message.decode(), addr)

        # Send the response message back to the client.

        room_socket.sendto(response.encode(),addr)


if __name__ == '__main__':
    main()

