"""Importing modules"""
import socket
import threading
import sys
import os
import json
from datetime import datetime
import time

#Specify IP and port number for incoming TCP/IP requests
HOST = sys.argv[1]
PORT = sys.argv[2]
def append_log(ip_address, port, msg_req, status):
    """Append request data to log file"""
    current_timestamp = datetime.now()
    timestamp_str = current_timestamp.strftime("%d-%b-%Y-%H:%M:%S")
    #Write tab-delimited lines to log file
    writing = ip_address+":"+port+"\t"+timestamp_str+"\t"+msg_req+"\t"+status+"\n"
    with open("server.log", "a") as server_log:
        server_log.write(writing)
        server_log.flush()
    return 0
class ThreadedServer():
    """Use multithreading to manage concurrent clients connecting to server"""
    #Initialize a server socket
    def __init__(self, host, port):
        self.host = host
        self.port = port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("Successfully initialized server socket.")
        except Exception as caught_error:
            print("Failed to initialize server socket. Error:", caught_error)
            sys.exit()
        #Bind socket to port
        try:
            self.sock.bind((host, port))
            print("Successfully bound socket on port", port)
        except Exception as caught_error:
            print("Failed to bind to port; currently unavailable/busy. Error:", caught_error)
            sys.exit()
    def listen(self):
        """Listen for incoming connections and initialize a new thread for each client"""
        print("Listening for incoming connections...")
        #Keep up to 5 pending client connections in queue
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            #Initialize a new thread for each client connection
            threading.Thread(target=self.client_listener, args=(client, address)).start()
    def client_listener(self, client, address):
        """Listen for messages from clients"""
        try:
            #Iterate through boards directory and save all boards to a list with assigned number
            def num_boards():
                #List all files in a directory using scandir()
                basepath = 'board/'
                boards = {}
                i = 1
                with os.scandir(basepath) as entries:
                    for entry in entries:
                        #Filter out only sub-directories
                        if not entry.is_file():
                            #Parse board names; replace underscores with spaces
                            board_name = str(entry.name).replace("_", " ")
                            boards[i] = board_name
                            i += 1
                return boards
            def GET_BOARDS():
                """Handle GET_BOARDS message"""
                #Calculate the most recent list of boards to send client
                boards = num_boards()
                num = len(boards)
                #Check the number of existing boards; if more than 0, proceed
                if num != 0:
                    #Send initial response to notify client that request was received successfully
                    client.sendall("Retrieving a list of existing message boards...".encode())
                    json_boards = json.dumps(boards).encode('utf-8')
                    charlen_boards = len(str(json_boards))
                    while True:
                        ready = client.recv(2048).decode()
                        if ready == "Ready":
                            client.sendall(str(charlen_boards).encode())
                            break
                    #Receive confirmation from client
                    while True:
                        waiting = client.recv(2048).decode()
                        if waiting == "sendDict":
                            #Send dictionary of boards to client
                            client.sendall(json_boards)
                            break
                    append_log(address[0], str(address[1]), "GET_BOARDS", "OK")
                #Otherwise, if no existing boards, return an error to the client and log it
                else:
                    append_log(address[0], str(address[1]), "GET_BOARDS", "Error")
                    print("No message boards defined.")
                    client.sendall("No message boards defined.".encode())
                    os._exit(1)
                #Send any other caught errors to client.
                return 0
            #Check that board at specified number exists
            def check_boardnum(msg):
                """Check that the supplied board number corresponds to an existing board"""
                client.sendall("Ready for board number".encode())
                whole_number = ''
                while True:
                    board_number = client.recv(2048).decode()
                    if board_number:
                        #Account for possibility of receiving very long numbers
                        whole_number += board_number
                        if whole_number.endswith("*"):
                            parsed_number = whole_number[:-1]
                            #If board exists, get the board title and call GET_MESSAGES
                            if parsed_number.isdigit():
                                if len(num_boards()) >= int(parsed_number) and int(parsed_number) != 0:
                                    board_name = num_boards()[int(parsed_number)].replace(" ", "_")
                                    return board_name
                            #If no board, return error to client and wait for new input
                                append_log(address[0], str(address[1]), msg, "Error")
                                client.sendall("Specified board does not exist. Try again.".encode())
                                return 1
                            #If supplied value is not a number, return error to client
                            append_log(address[0], str(address[1]), msg, "Error")
                            client.sendall("Specified board does not exist. Try again.".encode())
                            return 1
            def GET_MESSAGES(boardTitle):
                """Handle GET_MESSAGES message"""
                #Confirm received request from client
                client.sendall("Retrieving 100 most recent messages from board ".encode())
                #Retrieve 100 most recent messages from board
                basepath = 'board/'+boardTitle+'/'
                with os.scandir(basepath) as entries:
                    #Filter out only text files
                    txt_entries = []
                    for entry in entries:
                        if entry.is_file() and str(entry.name)[-4:] == ".txt":
                            txt_entries.append(str(entry.name))
                    #Sort txt files by title timestamp, newest-oldest
                    sorted_entries = sorted(txt_entries, key=lambda x: x[:14])
                    sorted_entries.reverse()
                    #Extract 100 most recent messages
                    if len(sorted_entries) > 100:
                        recent_entries = sorted_entries[:100]
                    else:
                        recent_entries = sorted_entries
                    #Assemble the nested dictionary of message titles and content
                    i = 1
                    messages = {}
                    for entry in recent_entries:
                        message_meta = {}
                        #Extract and parse post title
                        post_title = str(i) + ". " + entry[16:-4].replace("_", " ")
                        message_contents = open(basepath+entry, "r").readline()
                        #Extract message content
                        message_meta[post_title] = message_contents
                        messages[i] = message_meta
                        i += 1
                #Assemble messages in JSON object
                json_messages = json.dumps(messages).encode('utf-8')
                len_messages = len(str(json_messages))
                #Send number of bytes the client should expect to receive
                while True:
                    ready = client.recv(2048).decode()
                    if ready == "Ready":
                        client.sendall(str(len_messages).encode())
                        break
                #Receive confirmation from client
                while True:
                    waiting = client.recv(2048).decode()
                    if waiting == "sendDict":
                        #Send array of messages to client
                        client.sendall(json_messages)
                        break
                append_log(address[0], str(address[1]), "GET_MESSAGES", "OK")
                return 0
            def check_post_msg_param():
                """Confirm POST_MESSAGE parameters are valid"""
                #Get board title
                board_title = check_boardnum("POST_MESSAGE")
                if type(board_title) == str:
                    #Get post title
                    client.sendall("Ready for post title".encode())
                    while True:
                        #Receive length of expected post title
                        post_title_length = client.recv(2048).decode()
                        if post_title_length:
                            post_title_length = int(post_title_length)
                            client.sendall("Confirmed length".encode())
                            #Check if supplied post title is empty
                            if post_title_length == 0:
                                append_log(address[0], str(address[1]), "POST_MESSAGE", "Error")
                                client.sendall("Post title is empty. Please try again.".encode())
                                return 1
                            break
                    bits_received = 0
                    whole_post_title = ''
                    while True:
                        post_title = client.recv(2048).decode()
                        if post_title:
                            bits_received += 2048
                            whole_post_title += post_title
                            if bits_received >= post_title_length:
                                whole_post_title = whole_post_title.replace(" ", "_")
                                #Check if supplied contains only alphanumeric characters
                                if not whole_post_title.replace("_","").isalnum():
                                    append_log(address[0], str(address[1]), "POST_MESSAGE", "Error")
                                    client.sendall("Post title must be alphanumeric. Try again.".encode())
                                    return 1
                                #If input is valid, proceed
                                #Timestamp the title to put in filename
                                timestr = time.strftime("%Y%m%d-%H%M%S")
                                parsed_post_title = timestr+"-"+whole_post_title
                                break
                    #Get message content
                    client.sendall("Ready for message content".encode())
                    while True:
                        message_length = client.recv(2048).decode()
                        if message_length:
                            message_length = int(message_length)
                            client.sendall("Confirmed length".encode())
                            if message_length == 0:
                                append_log(address[0], str(address[1]), "POST_MESSAGE", "Error")
                                client.sendall("Empty message content. Please try again.".encode())
                                return 1
                            bits_received = 0
                            whole_message = ''
                            break
                    while True:
                        messageContent = client.recv(2048).decode()
                        if messageContent:
                            bits_received += 2048
                            whole_message += messageContent
                            if bits_received >= message_length:
                                #Upon validating client parameters are valid, call POST_MESSAGE
                                POST_MESSAGE(board_title, parsed_post_title, whole_message)
                                return 0
                else:
                    append_log(address[0], str(address[1]), "POST_MESSAGE", "Error")
                return 1
            def POST_MESSAGE(boardTitle, postTitle, messageContent):
                """Handle POST_MESSAGE message"""
                try:
                    #Send confirmation POST_MESSAGE request successful
                    basepath = 'board/'+boardTitle+'/'
                    filename = postTitle+'.txt'
                    with open(os.path.join(basepath, filename), 'w') as temp_file:
                        temp_file.write(messageContent)
                    client.sendall("New post added successfully.".encode())
                    append_log(address[0], str(address[1]), "POST_MESSAGE", "OK")
                    return 0
                except OSError:
                    append_log(address[0], str(address[1]), "POST_MESSAGE", "Error")
                    client.sendall("Post title exceeds file name length supported by OS.".encode())
                    return 1
            while True:
                data = client.recv(2048)
                msg = data.decode()
                #GET_BOARDS
                if msg == "GET_BOARDS":
                    GET_BOARDS()
                #GET_MESSAGES
                if msg == "GET_MESSAGES":
                    #Check if the board at the specified number exists
                    #If not, check_boardnum() will throw an error
                    boardTitle = check_boardnum("GET_MESSAGES")
                    #Otherwise, retrieve 100 most recent messages from the specified board
                    if type(boardTitle) == str:
                        GET_MESSAGES(boardTitle)
                #POST_MESSAGE
                if msg == "POST_MESSAGE":
                    check_post_msg_param()
                #Deal with invalid requests from client; return an error and wait for new input
                if msg not in ("GET_BOARDS", "GET_MESSAGES", "POST_MESSAGE"):
                    append_log(address[0], str(address[1]), "INVALID_MSG", "Error")
                    client.sendall("Invalid message. Please try again.".encode())
            print("Client at ", address, " has disconnected from the server.")
        except BrokenPipeError:
            print("Client at ", address, " has disconnected from the server.")
            pass
if __name__ == "__main__":
    try:
        ThreadedServer(HOST, int(PORT)).listen()
    except:
        print("Server disconnected.")
        os._exit(1)
