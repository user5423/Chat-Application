import socket
import argparse
import threading
from typing import Dict, Optional, Union
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import time
from message import clientConnection

##TODO: Go through the code and external libraries to check for potential exceptions
##BUG: When server disconnects, an error message is only sometimes displayed, always exists though

class clientMessenger:
    def __init__(self) -> None:
        self.sock = self.createClientSocket()
        self.clientConnection = clientConnection(self.sock)
        self.exit_flag = threading.Event()

        self.designmessage = \
        """
        This application is strictly supported on Windows only, rather than Linux. This is because\n
        1. No/Limited compatability in terminal interface manipulation between platforms (this extends to TUIs)
        =====> e.g. GNU Readlines, ncurses, msvcrt, urwid etc.
        2. Design differences caused by platform  differences
        =====> e.g. Input() Calls will hang on Windows since you cannot select() stdin to sidestep this issue (unlike Linux)
        3. Differences in threading
        =====> e.g. Python daemon Threads fail to be killed during process termination on Linux (unlike Windows)
        4. Differences in signal
        =====> e.g. signal.SIGALRM doesn't exist in Windows (unlike), and other signals have different side-effects on different platforms

        Even when there is platform reimplementations, there's often side-effects or bugs

        --> I actually spent more time attempting full cross-compatability the on the actual networking part
        --> Therefore a conscious design decision was made to stick with a single platform in order to provide a more robust application
        """
        
    def createClientSocket(self) -> None:
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def exit(self) -> None: 
        self.exit_flag.set()

    def close(self) -> None: 
        try:
            self.sock.close()
        except OSError:
            print(f"Localhost: Underlying issue with releasing connection resources")
        except socket.error as msg:
            print(f"Localhost: {str(msg).split(':')[-1].strip()}")

    def run(self, USER: str, HOST: str, PORT: int) -> None:
        ##TODO: encapsulate the below lines into a function for sock
        self.USER = USER
        self.sock.setblocking(1)
        if self.connect(HOST, PORT) is False: return

        message =  self.registerUser(USER)
        self.processRetrievedMessage(message)
        if self.exit_flag.is_set(): return

        t1 = threading.Thread(target=self.output)
        t2 = threading.Thread(target=self.input, daemon=True)
        t1.start()
        t2.start()

        self.exit_flag.wait()
        t1.join(0)
        self.close()
        
    def output(self) -> None:
        while self.exit_flag.is_set() is False:
            message = self.clientConnection.receiveRequest()
            self.processRetrievedMessage(message)

    def input(self) -> None:
        session = PromptSession()
        with patch_stdout():
            while self.exit_flag.is_set() is False:
                try:
                    result = session.prompt(f"{self.USER}: ", )
                    if self.exit_flag.is_set() is True: break
                    self.clientConnection.sendRequest(user=self.USER, message=result)
                except KeyboardInterrupt:
                    self.exit_flag.set()

    def connect(self, HOST: str, PORT: int) -> bool:
        try:
            self.sock.connect((HOST, PORT))
            return True
        except ConnectionRefusedError:
            print("Localhost: The target machine is refusing connections")
        except socket.gaierror:
            print("Localhost: Failed to resolve the provided hostname")
        except socket.error as msg:
            print(f"Localhost: {str(msg).split(':')[-1].strip()}")
        return False

    def registerUser(self, USER: str) -> Optional[str]:
        print(f"Localhost: Attempting to register with name '{USER}'")
        self.clientConnection.sendRequest(user=USER, messageType="User-Creation")
        return self.clientConnection.receiveRequest()

    def processRetrievedMessage(self, message: Optional[Dict[str, Union[Dict[str, str], str]]]) -> None:
        violatingTypes = {"Session-Rejection"}
        if message == None or message["Headers"]["Message-Type"] in violatingTypes:
            self.terminateSession(message)
        else:
            self.displayMessage(message) ## TODO: Maybe perform more than just display

    def displayMessage(self, message: Dict[str, Union[Dict[str, str], str]]) -> None:
        print(message["Body"])
    
    def terminateSession(self, message):
        if message == None and self.exit_flag.is_set():
            print("Localhost: The Client has terminated the session")
        elif message == None and not self.exit_flag.is_set():
            print("Localhost: The Server has disconnected from the session", flush=True)
            ## NOTE: The prompt_toolkit library logic with the hanging "input/prompt" thread causes a bug
            ## FIXED: By context switching and then printing, the outcome of this bug is circumvented
            self.exit_flag.wait(0.04)
            print("\r\n", flush=True)
        elif message["Headers"]["Message-Type"] == "Session-Rejection":
            print("Server: The Server has rejected the session-creation")
        elif message["Headers"]["Message-Type"] == "Session-Termination":
            print("Server: The Server has terminated the session")
        # time.sleep(5)
        self.exit_flag.set()
            
def parseArguments() -> None:
    parser = argparse.ArgumentParser(description="A application to provide IM services to clients")
    parser.add_argument("user", type=str)
    parser.add_argument("host", type=str)
    parser.add_argument("port", type=int)
    return parser.parse_args()

def main():
    args = parseArguments()
    cm = clientMessenger()
    cm.run(args.user, args.host, args.port)

if __name__ == "__main__":
    main()
