import unittest
import sys
sys.path.insert(0, "..\\")
from src.message import request, response


class testRequest(unittest.TestCase):
    def setUp(self):
        self.req = request()


    def test_setStringRequest(self):
        print("\n")
        ## Test when message is 0 sized length
        print("Test when request message is 0 sized length")
        self.req.setStringRequest("")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:0\r\n\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)


        ## Test when the request obect contains a non-zero length message
        print("Test when request message is non-zero sized length")
        self.setUp()
        self.req.setStringRequest("New Request Object")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:18\r\nNew Request Object\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)


        ## Test when the request object is reused
        print("Test when request object is reused")
        self.req.setStringRequest("Reused")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:6\r\nReused\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)


        ## Test when the request contains characters that are \r\n
        print("Test whether request message escapes newline correctly")
        self.req.setStringRequest("\n")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:3\r\n\\n\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)


        print("Test whether request message escapes carriage return correctly")
        self.req.setStringRequest("\r")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:3\r\n\\r\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)


        ## Test when the request contains characters that are \r\n
        print("Test whether request message escapes line terminator correctly")
        self.req.setStringRequest("\r\n")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:6\r\n\\r\\n\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)


        ## Test when the request contains characters that are \r\n\r\n
        print("Test whether request message escapes terminator sequence correctly")
        self.req.setStringRequest("\r\n\r\n")
        expectedOutput = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:12\r\n\\r\\n\\r\\n\r\n\r\n"
        self.assertEqual(self.req.rawRequest, expectedOutput)

        print("\n\n")


class testResponse(unittest.TestCase):
    def setUp(self):
        self.resp = response()

    def test_setRawRequest(self):
        print("\n")
        ##Test when message is 0 sized length
        print("Test when request message is 0 sized length")
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:0\r\n\r\n\r\n"
        expectedOutput = ""
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])

        print("Test when response message is non-zero sized length")
        self.setUp()
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:18\r\nNew Request Object\r\n\r\n"
        expectedOutput = "New Request Object"
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])


        print("Test when response object is reused")
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:18\r\nReused\r\n\r\n"
        expectedOutput = "Reused"
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])


        print("Test whether request message escapes newline correctly")
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:3\r\n\\n\r\n\r\n"
        expectedOutput = "\n"
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])


        print("Test whether request message escapes carriage return correctly")
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:3\r\n\\r\r\n\r\n"
        expectedOutput = "\r"
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])


        print("Test whether request message escapes line terminator correctly")
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:6\r\n\\r\\n\r\n\r\n"
        expectedOutput = "\r\n"
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])


        print("Test whether request message escapes terminator sequence correctly")
        inputBytes = b"Message-Type:User-Message\r\nContent-Type:Text\r\nContent-Length:12\r\n\\r\\n\\r\\n\r\n\r\n"
        expectedOutput = "\r\n\r\n"
        self.resp.setRawRequest(inputBytes)
        self.assertEqual(expectedOutput, self.resp.stringRequest["body"])



unittest.main()