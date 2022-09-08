import unittest
import sys
sys.path.insert(0, "..\\src")

from src.server import chatObject


class testChatObject(unittest.TestCase):
    def setUp(self):
        self.chatObject = chatObject()


    def test_logUserMessage(self):
        self.setUp()
        

    def test_registerUser(self):
        USER = "user5423"
        USER2 = "admin"
        ##Testing register of user
        self.chatObject.registerUser(USER)
        
        expectedOutput = [f"{USER} has just joined the server!"]
        self.assertEqual(self.chatObject.chat, expectedOutput)

        expectedOutput = [f""]
        self.assertEqual()
        ...

    ##We want to test registerUser
    ##--> Registering a already registered User
    ##--> Registering a user properly