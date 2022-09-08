import argparse
import selectors
import socket
import signal
import logging
from datetime import datetime
from collections import namedtuple
from typing import Dict, Iterable, List, NamedTuple, Optional, Union
from message import connections, clientConnection

##TODO: Restructure the class hierarchies into application, session, connection (or app/session and connection)
##TODO: Use enum types for better code quality
##TODO: Consider whether we need to strip \r or \n from the end of a line when storing messages in the chatObject
##TODO: Design the logging system to write to the log file

##FUTURE: Have a function to setup a "SERVER" admin user

class chatObject:
    def __init__(self) -> None:
        ## When a user registers, we set a pointer to the top of the stack
        ## NOTE: Not using deque because it doesn't support slicing
        self.chat: List[NamedTuple] = [] ## This can result in a memory leak, so we should store the remaining
        self.userPointers: Dict[str, int] = {}
        self.chatAction: NamedTuple = namedtuple("ChatAction", ["datetime", "user", "message", "visibility"])
    
    def logUserMessage(self, user: str, messageString: str, visibility: str = "public") -> None:
        ca = self.chatAction(datetime.now(), user, messageString, visibility)
        self.chat.append(ca)

    def logServerMessage(self, messageString: str, visibility="public") -> None:
        self.chat.append(self.chatAction(datetime.now(), "Server", messageString, visibility))

    def getNewChats(self, user: str) -> Optional[List[NamedTuple]]:
        if self.userPointers.get(user) >= len(self.chat): return None
        pointer = self.userPointers.get(user)
        self.userPointers[user] = len(self.chat)
        ret = [chat for chat in self.chat[pointer:] if chat.visibility == "public" and chat.user != user]
        return None if len(ret) == 0 else ret

    def registerUser(self, user: str) -> None:
        self.userPointers[user] = len(self.chat)
        self.logServerMessage(f"{user} has just joined the server!")
    
    def unregisterUser(self, user: str) -> None:
        del self.userPointers[user]
        self.logServerMessage(f"{user} has just left the server!")


class messengingServer:
    def __init__(self) -> None:
        self.registeredUsers: Dict[str, bool] = {}
        self.reservedNames = {"Server", "bot", "helper", "localhost"}
        self.chat: chatObject = chatObject()
        self.eventLoopFlag: bool = True
        self.logfile = "server.log"
        logging.basicConfig(filename="server.log", level=logging.DEBUG)
        self.userServices = {"User-Creation": self.__serviceUserCreation, "User-Message": self.__serviceUserMessage, "User-Command": self.__serviceUserCommand}
        self.setupSignalHandlers()

    def _setup(self, PORT: int) -> None:
        self.PORT: int = PORT
        self.HOST: str = "127.0.0.1"
        self.connections: connections = connections()
        self.selector: selectors.DefaultSelector = selectors.DefaultSelector()
        self.serverSocket: socket.socket = None
        return self.__setupServerSocket()

    def setupSignalHandlers(self):
        try:
            signal.signal(signal.SIGBREAK, self.sig_handler)
        except AttributeError: pass ## Avoid errors caused by OS differences
        try:
            signal.signal(signal.SIGINT, self.sig_handler)
        except AttributeError: pass ## Avoid errors caused by OS differences

    def run(self) -> None:
        args = self.parseArguments()
        if self._setup(args.port) is True:
            self.logDebug("Server", "Server-Setup", "Success")
            return self._executeEventLoop()
        else:
            self.logDebug("Server", "Server-Setup", "Failure")
        return False

    def _executeEventLoop(self) -> None:
        self.logDebug("Server", "Server-Running", "Success")
        while self.eventLoopFlag:
            events = self.selector.select(timeout=2.0)
            for selectorKey, bitmask in events:
                if selectorKey.data == "ServerSocket":
                    self.__acceptConnection()
                else:
                    self.__serviceConnection(selectorKey, bitmask)
        try:
            print("Server is Terminating")
            self.closeRemainingSessions()
            self.closeRemainingConnections()
            self.serverSocket.close()
            self.logDebug("Server", "Server-Termination", "Success")
        except (KeyboardInterrupt, Exception):
            self.logDebug("Server", "Server-Termination" "Warning")


    def closeRemainingSessions(self) -> None:
        for user, cc in list(self.connections.userToConnection.items()):
            self.closeSession(user, cc)
    
    def closeRemainingConnections(self) -> None:
        for cc in list(self.connections.filenoToConnection.values()):
            self.connections.unregisterConnection(cc)

    def __setupServerSocket(self) -> None:
        if self.__createServerSocket() == False: return False
        self.__registerServerSocket()
        print(f"Server listening on {self.HOST}:{self.PORT}\n\n")
        return True

    ##TODO: Provide exception handling for setting up the server sock
    def __createServerSocket(self) -> bool:
        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSocket.bind((self.HOST, self.PORT))
            self.serverSocket.listen()
            self.serverSocket.setblocking(False)
            return True
        except OSError:
            print(f"Socket Setup Error: The address has already been bound")
        except socket.error as e:
            print(f"Socket Setup Error: {e}")
        return False

    def __registerServerSocket(self) -> None:
        self.selector.register(self.serverSocket, selectors.EVENT_READ, data="ServerSocket")

    def __acceptConnection(self) -> None:
        conn, _ = self.serverSocket.accept()
        cc = clientConnection(conn)
        hostname, port = cc.sock.getpeername()
        self.connections.registerConnection(cc)
        self.selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data="connection")
        logging.info(f"{datetime.now()}\t{hostname}\t{port}\tUndefined\tConnection-Accepted\tSuccess")
        

    def __serviceConnection(self, selectorKey: selectors.SelectorKey, bitmask: int) -> None:
        conn = self.connections.filenoToConnection[selectorKey.fd]
        user = self.connections.userToConnection.inverse.get(conn)

        if bitmask & selectors.EVENT_READ:
            message = conn.receiveRequest()
            if message == None:
                # print("The connection has been closed by the client")
                return self.closeSession(user, conn)
            elif user == None and message["Headers"]["Message-Type"] != "User-Creation":
                # print("You're first message must be a user-creation type message")
                return self.closeSession(user, conn)
            elif user != None and message["Headers"]["Message-Type"] == "User-Creation":
                # print("You can only register a single user on a connection")
                return self.closeSession(user, conn)
            else:
                self.__serviceMessage(message, conn)

        if bitmask & selectors.EVENT_WRITE:
            isRegistered = self.registeredUsers.get(user)
            if isRegistered == False:
                conn.sendRequest(user="Server", message="Server: Succesfully registed", messageType="User-Creation")
                self.registeredUsers[user] = True
            elif isRegistered == True:
                self.pushUpdatedChats(conn)
     
    def closeSession(self, user: str, conn: clientConnection) -> None:
        try:
            self.logEvent(user, "Session-Termination", "Success")
            self.logEvent(user, "Connection-Termination", "Success")
            hostname, port = conn.sock.getpeername()
            print(f"{datetime.now()}\t{hostname}\t{port}\t{user}\tSession-Termination")
            self.selector.unregister(conn.sock)
            self.connections.close(user, conn)
            self.chat.unregisterUser(user)
            del self.registeredUsers[user]
        except Exception:
            self.logEvent(user, "Session-Termination", "Warning")
            self.logEvent(user, "Connection-Termination", "Warning")



    def createSession(self, user: str, conn: clientConnection) -> None:
        ## This registers a new user to the new connection
        hostname, port = conn.sock.getpeername()
        print(f"{datetime.now()}\t{hostname}\t{port}\t{user}\tSession-Creation")
        self.registeredUsers[user] = False ##TODO: Consider redundant variable
        self.connections.registerUser(user, conn)
        self.chat.registerUser(user)
        self.logEvent(user, "Session-Creation", "Success")
        

    def rejectSessionCreation(self, user: str, conn: clientConnection) -> None:
        ## This closes a connection that attempt to register a new user that violated some condition
        message = f"Server: The username {user} is either in use or a reserved username."
        messageType = "Session-Rejection"
        conn.sendRequest(user, messageType=messageType, message=message, contentType="Text")
        self.connections.unregisterConnection(conn)
        self.selector.unregister(conn.sock)
        self.logEvent(user, "Session-Rejection", message)
        conn.close()


    def __serviceMessage(self, message: str, conn: clientConnection) -> None:
        messageString, messageUser, messageType = self.__extractDataFromMessage(message)
        try:
            self.userServices[messageType](conn=conn, user=messageUser, message=messageString)
        except KeyError: return print(f"Message-Type not found: {messageType}")

    def __extractDataFromMessage(self, message: Dict[str, Union[Dict[str, str], str]]) -> Iterable[str]:
        return message["Body"], message["Headers"]["User"], message["Headers"]["Message-Type"]

    def pushUpdatedChats(self, conn: clientConnection) -> None:
        try:
            user = self.connections.userToConnection.inverse[conn]
        except KeyError: return None
        ##We get the chats that the user has missed
        chats = self.chat.getNewChats(user)
        if chats == None: return None
        ##We now need to decide how we will send this -- We can either send it grouped, or individually. I personally would go with through grouped
        messageString = self.generateUpdatedChatMessage(chats)
        ##We then create a request and send it to the session endpoint
        conn.sendRequest(user="Server", message=messageString, messageType="Chat-Update")

    def generateUpdatedChatMessage(self, chats: List[NamedTuple]):
        return "".join([f"{chat.user}: {chat.message}" for chat in chats])

    def __serviceUserCommand(self, **kwargs) -> None:
        self.logMessage(kwargs["user"], "User-Command", kwargs["message"])
        raise NotImplementedError

    def __serviceUserMessage(self, **kwargs) -> None:
        self.logMessage(kwargs["user"], "User-Message", kwargs["message"])

    def logMessage(self, user: str, description: str, message: str, visibility: str = "public") -> None:
        self.chat.logUserMessage(user, message, visibility)       

    def logDebug(self, user: str = "Server", eventType: str = "Default", description: str = "Default",) -> None:
        logging.debug(f"{datetime.now()}\t{self.HOST}\t{self.PORT}\t{user}\t{eventType}\t{description}")
        
    def logEvent(self, user: str, eventType: str, description: str) -> None:
        if user not in self.reservedNames:
            hostname, port = self.connections.userToConnection[user].sock.getpeername()
        else:
            hostname, port = self.HOST, self.PORT
        logging.info(f"{datetime.now()}\t{hostname}\t{port}\t{user}\t{eventType}\t{description}")

    def __serviceUserCreation(self, **kwargs) -> None:
        user, conn = kwargs["user"], kwargs["conn"]
        if user not in self.registeredUsers and user not in self.reservedNames:
            self.createSession(user, conn)
        else:
            self.rejectSessionCreation(user, conn)

    def exit(self) -> None:
        self.eventLoopFlag = False
    
   ## Required parameters by signal handler
    def sig_handler(self, signum, frame) -> None:
        self.exit()

    def parseArguments(self) -> None:
        parser = argparse.ArgumentParser(description="A Multi-Client Instant Messaging Service")
        parser.add_argument("port", type=int)
        return parser.parse_args()

def main():
    ms = messengingServer()
    ms.run()

if __name__ == "__main__":
    main()