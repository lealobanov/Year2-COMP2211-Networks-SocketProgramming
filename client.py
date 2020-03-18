"""Importing modules"""
import socket
import sys
import json
#Specify IP and port number to attempt to connect to
HOST = sys.argv[1]
PORT = sys.argv[2]
#Create a TCP/IP socket
try:
    socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Successfully initialized client socket.")
except Exception as caught_error:
    print("Failed to initialize client socket. Error: ", caught_error)
    sys.exit()
#Connect socket to the port where the server is listening
SERVER_ADDRESS = (HOST, int(PORT))
try:
    socket.connect(SERVER_ADDRESS)
    print("Successfully connected to port", PORT)
    #Configure socket to timeout request if no server response received within 10 seconds
    socket.settimeout(10)
#If server is not running or unavailable, print error and exit
except Exception as caught_error:
    print("Error connecting to server: ", caught_error)
    sys.exit()
def get_boards():
    """Interact with server during request to GET_BOARDS"""
    while True:
        #Get confirmation from server that message was received successfully
        initial_response = socket.recv(2048).decode()
        #If no defined message boards, return an error and exit the program
        if initial_response == "No message boards defined.":
            print("Server returned an error: "+initial_response)
            sys.exit()
        if initial_response == "Retrieving a list of existing message boards...":
            print(initial_response)
            break
    #Tell server ready to receive boards
    socket.sendall("Ready".encode())
    #Wait for server to calculate character length of message boards
    while True:
        array_length = socket.recv(2048).decode()
        if array_length:
            array_length = int(array_length)
            socket.sendall("sendDict".encode())
            break
    #Accept that many data inputs, printing them to screen
    bits_received = 0
    entire_boards = b''
    while True:
        boards = socket.recv(2048)
        if boards:
            bits_received += 2048
            entire_boards += boards
            if bits_received >= array_length-3:
                boards = json.loads(entire_boards.decode('utf-8').replace('\r\n', ''))
                break
    for board in boards:
        print(board+"."+boards[board])
    return 0
def get_messages(board_number):
    """Gets a list of 100 most recent messages in a particular board, printed newest-oldest"""
    #Send server GET_MESSAGES
    socket.sendall("GET_MESSAGES".encode())
    #Send server number of desired board
    while True:
        initial_response = socket.recv(2048).decode()
        if initial_response == "Ready for board number":
            board_number = board_number + "*"
            socket.sendall(board_number.encode())
            break
    #Wait for server to confirm that request was received successfully
    while True:
        confirm_request = socket.recv(2048).decode()
        #If the board at the specified number is not defined, the server returns an error
        if confirm_request == "Specified board does not exist. Try again.":
            print(confirm_request)
            break
        #Otherwise, get confirmation from the server that the request was successful
        if confirm_request == "Retrieving 100 most recent messages from board ":
            print(confirm_request + board_number[:-1] + " ...")
            #Tell server ready to receive messages
            socket.sendall("Ready".encode())
            #Wait for server to calculate character length of messages
            while True:
                array_length = socket.recv(2048).decode()
                if array_length:
                    array_length = int(array_length)
                    socket.sendall("sendDict".encode())
                    break
            #Accept that many bytes of data
            bits_received = 0
            entire_array = b''
            while True:
                messages = socket.recv(2048)
                if messages:
                    bits_received += 2048
                    entire_array += messages
                    if bits_received >= array_length-3:
                        entire_array.decode()
                        messages = json.loads(entire_array)
                        break
            #If no messages contained in board, notify client
            if len(messages) == 0:
                print("No messages found in this board.")
            else:
                #Print each message's title and content to the screen
                for entry in messages:
                    meta = (messages[entry])
                    for key, value in meta.items():
                        print(key)
                        print(" ")
                        print(value)
            break
    return 0
def collect_new_post_data():
    """Collect data for new post parameters"""
    #Collect and save user input for destination board, post title, and message content
    board_title = input("Specify the number of the destination board: ")
    post_title = input("Specify the title of your new post: ")
    message_content = input("Please provide the message content: ")
    new_post(board_title, post_title, message_content)
#Create a new message and post it to a specified board
def new_post(board_title, post_title, message_content):
    """Send POST_MESSAGE message and parameters to server"""
    socket.sendall("POST_MESSAGE".encode())
    #Send server message parameters
    while True:
        initial_response = socket.recv(2048).decode()
        #Send number of desired board to post on
        if initial_response == "Ready for board number":
            board_title = board_title+"*"
            socket.sendall(board_title.encode())
            break
    #Wait for server to confirm that board number was received succesfully
    while True:
        confirm_request = socket.recv(2048).decode()
        #If the board at the specified number is not defined, the server returns an error
        if confirm_request == "Specified board does not exist. Try again.":
            print(confirm_request)
            return 1
        #Otherwise, proceed to transfer post title
        if confirm_request == "Ready for post title":
            #Send length of anticipated post title
            expected_length = str(len(post_title))
            socket.sendall(expected_length.encode())
            break
    #Wait for the server to confirm that post title length was received, then send the post title
    while True:
        confirm_request = socket.recv(2048).decode()
        if confirm_request == "Confirmed length":
            socket.sendall(post_title.encode())
            #Catch any errors, otherwise proceed to send message content
            while True:
                confirm_request = socket.recv(2048).decode()
                if confirm_request == "Post title is empty. Please try again.":
                    print(confirm_request)
                    return 1
                if confirm_request == "Post title must be alphanumeric. Try again.":
                    print(confirm_request)
                    return 1
                if confirm_request == "Ready for message content":
                    #Send length of anticipated message
                    expected_length = str(len(message_content))
                    socket.sendall(expected_length.encode())
                    break
            break
    #Upon receiving confirmation from server, send the message
    while True:
        confirm_request = socket.recv(2048).decode()
        if confirm_request == "Confirmed length":
            socket.sendall(message_content.encode())
            #Wait for confirmation that new post was added successfully, else return an error
            while True:
                confirm_request = socket.recv(2048).decode()
                if confirm_request == "Empty message content. Please try again.":
                    print(confirm_request)
                    return 1
                if confirm_request == "Post title exceeds file name length supported by OS.":
                    print(confirm_request)
                    return 1
                if confirm_request == "New post added successfully.":
                    print(confirm_request)
                    return 0
try:
    #Upon establishing connection, retrieve a list of all existing boards and print them to the screen
    socket.sendall("GET_BOARDS".encode())
    get_boards()
    #Perpetually wait for user input
    while True:
        #Send commands to server
        MESSAGE = input("Enter a message: ")
        print("Sending your message...")
        #Quit the program and close connection to client socket
        if MESSAGE == "QUIT":
            break
        #Return 100 most recent messages from board listed at specified number
        elif MESSAGE.isdigit():
            get_messages(MESSAGE)
        elif MESSAGE == "GET_BOARDS":
            print("List of existing boards has already been retrieved.")
        #Initiate a new post to an existing board
        elif MESSAGE == "POST":
            collect_new_post_data()
        #Deal with user attempts to send an empty message
        elif MESSAGE == '':
            print("Empty input. Please try again.")
        #Return appropriate server response for all other types of (invalid) messages
        elif MESSAGE:
            socket.sendall(MESSAGE.encode())
            while True:
                SERVER_RESPONSE = socket.recv(2048).decode()
                print(SERVER_RESPONSE)
                if not SERVER_RESPONSE:
                    print("Server disconnected.")
                    sys.exit()
                break
    #Close the socket upon receiving QUIT from client and breaking out of the infinite while loop
    socket.close()
except BrokenPipeError:
    print("Server disconnected.")
    sys.exit()
except ConnectionResetError:
    print("Server disconnected.")
    sys.exit()
except KeyboardInterrupt:
    print("Connection terminated.")
    sys.exit()