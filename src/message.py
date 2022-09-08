
import socket
from bidict import bidict
from typing import Optional, List, Dict

##TODO: Replace safeEncodeValues/safeDecodeValues to escapeCharacters
##TODO: Consider how the above methods will escape characters, and which characters they will escape
##A simplified protocol inspired from the HTTP Protocol
class request:
    def __init__(self) -> None:
        self.rawRequest: bytes = b""
        self.stringRequest: str = ""

    def setStringRequest(self, user: str, message: str = "", messageType="User-Message", contentType: str = "Text") -> None:
        self.stringRequest = message
        self.rawRequest = self.createRawRequest(user, message, messageType, contentType)

    ##TODO: These variables should be provided in when setRequest is set
    def createRawRequest(self, user: str, message: str, messageType: str, contentType: str) -> bytes:
        string = ""
        ##First we want to see if there are any values that we want to safely encode here
        body = message.encode("unicode-escape").decode("utf-8")
        ##Then we want to get the neccessary headers
        string += f"User:{user}\r\n"
        string += f"Message-Type:{messageType}\r\n"
        string += f"Content-Type:{contentType}\r\n"
        string += f"Content-Length:{len(repr(body)) - 2}\r\n" ## -2 to remove the two quotes that repr() produces
        ##Then we add the body (i.e. the message)
        string += f"{body}\r\n\r\n"
        return string.encode("utf-8")


class response:
    def __init__(self) -> None:
        self.rawRequest: bytes = b""
        self.stringRequest: str = ""

    def setRawRequest(self, bytesRequest: bytes) -> None:
        try:
            self.rawRequest = bytesRequest
            self.stringRequest = self.createStringRequest(bytesRequest)
        except Exception:
            self.stringRequest = None

    def createStringRequest(self, bytesRequest: bytes) -> None:
        string = bytesRequest.decode("utf-8").split("\r\n")[:-2]
        return {"Headers": self.parseHeaders(string), "Body": self.parseBody(string)}

    def parseHeaders(self, splitString: List[str]) -> Dict[str, str]:
        return dict(split.rstrip("\r\n").split(":") for split in splitString[:-1])

    def parseBody(self, splitString: List[str]) -> str:
        return splitString[-1].encode("utf-8").decode("unicode-escape")


##Once one side has created a message object which has been encoded into a bytes object
##The next thing to do is to send it to the destination socket
## --> That means that we need to hold the other pair of that comms in the class clientConnection
##TODO: Rename this to connectionRegistry, or connectionDictionary or sessions
class connections:
    def __init__(self) -> None:
        self.filenoToConnection: bidict[socket.fileno, clientConnection] = bidict()
        self.userToConnection: bidict[str, clientConnection] = bidict()

    def registerConnection(self, connection: "clientConnection") -> None:
        self.filenoToConnection[connection.sock.fileno()] = connection

    def unregisterConnection(self, connection: "clientConnection") -> None:
        try:
            self.filenoToConnection.pop(connection.sock.fileno())
        except KeyError: pass

    def registerUser(self, user: str, connection: "clientConnection") -> None:
        self.userToConnection[user] = connection

    def unregisterUser(self, user: str) -> None:
        try:
            self.userToConnection.pop(user)
        except KeyError: pass
        
    def close(self, user: str, connection: "clientConnection") -> None:
        self.unregisterConnection(connection)
        self.unregisterUser(user)
        connection.close()
        

##TODO: Consider changing the name to something else maybe just connection -- If named to connection, name connections class to something else
class clientConnection:
    def __init__(self, socket: socket.socket) -> None:
        self.sock = socket
        self.sock.setblocking(False)
        self.req = request()
        self.resp = response()

    def sendRequest(self, user: str, message: str = "", messageType: str = "User-Message", contentType: str = "Text") -> None:
        self.req.setStringRequest(user, message, messageType, contentType)
        return self.sock.sendall(self.req.rawRequest)

    def receiveRequest(self) -> Optional[str]:
        self.resp.setRawRequest(self.receiveMessage())
        return None if self.resp.stringRequest == "" else self.resp.stringRequest

    def receiveMessage(self) -> None:
        ##NOTE: Message end should also be signified by len(output) == 0
        buffer = b""
        bufferSize = 1024
        terminationStr = b"\r\n\r\n"
        while bufferSize >= 1024:
            try:
                output = self.sock.recv(1024)
            except (ConnectionAbortedError, ConnectionResetError, socket.error): break
            
            buffer += output
            bufferSize = len(output)
            if terminationStr in buffer: break

        return buffer

    def close(self) -> None:
        self.sock.close()
