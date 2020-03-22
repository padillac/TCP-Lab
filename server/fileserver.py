
import sys, os, socket, time
from multiprocessing import Process, Lock


class FileServer:
    def __init__(self):
        self.stdoutLock = Lock()
        iface, port, storageDir = self.read_config_file()
        self.port = port
        self.host = iface
        self.storageDir = storageDir
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        
  
        


    def read_config_file(self):
        with open("fileserver.conf", 'r') as conf:
            for line in conf.readlines():
                if line[0] == '#':
                    continue
                line = line.split(":")
                if line[0].strip() == "Interface":
                    iface = line[1].strip()
                if line[0].strip() == "Port":
                    port = int(line[1].strip())
                if line[0].strip() == "StorageDirectory":
                    storageDir = line[1].strip()
        return iface, port, storageDir


    def safe_print(self, s):
        self.stdoutLock.acquire()
        print(s)
        self.stdoutLock.release()


    def looper(self):
        self.safe_print("Serving files from: {0}".format(self.storageDir))
        listenerProcess = Process(target=self.listen)
        listenerProcess.start()
        # Input handler:
        while True:
            time.sleep(.1)
            c = input(">")
            
            if c == "exit":
                self.safe_print("exiting..")
                listenerProcess.terminate()
                exit()



    def listen(self):
        
        self.safe_print("Listening on {0}:{1}..".format(self.host, self.port))
        self.sock.listen(10)

        while True:
            clientSock, clientAddr = self.sock.accept()
            self.safe_print("\n-- New connection received from {0}".format(clientSock.getpeername()))

            newSock = socket.socket()
            newSock.bind((self.host, 0))
            freePort = newSock.getsockname()[1]
            newSock.close()
            Process(target=self.connection_manager, args=(freePort,)).start()

            self.safe_print("Routing to new socket on port: {0}".format(freePort))

            clientSock.sendall(str(freePort).encode())
            clientSock.close()


    def connection_manager(self, p):
        newSock = socket.socket()
        newSock.bind((self.host,p))
        newSock.settimeout(10)
        newSock.listen(0)
        self.safe_print("Handler created on {0}".format(p))
        try:
            clientSock, clientAddr = newSock.accept()
        except socket.timeout:
            return        
        

        rawdata = clientSock.recv(1024).decode("ascii").strip()
        if not rawdata:
            clientSock.close()
            return
        
        ################################################# HANDLE FILE UPLOADS AND REQUESTS
        msg = rawdata.split()

        self.safe_print("Received message: " + str(msg))

        # List files
        if msg[0] == "l":
            if len(msg) > 1:
                path = os.path.join(self.storageDir, msg[1])
            else:
                path = self.storageDir
            fileList = os.listdir(path)

            if len(fileList) == 0:
                response = "<Empty>"
            else:
                response = ""
                for f in fileList:
                    response += f + "\n"
            clientSock.sendall(response.encode())


        # Download file
        if msg[0] == 'd':
            filePath = os.path.join(self.storageDir, msg[1])
            self.safe_print("Client on {0} requested file: {1}".format(clientAddr, filePath))
            try:
                with open(filePath, 'rb') as f:
                    clientSock.sendfile(f)
                    self.safe_print("Sent.")
            except:
                self.safe_print("!-- Error sending requested file {0} on port {1}".format(filePath, clientAddr))
                clientSock.close()
                return


        # Upload file
        if msg[0] == 'u':
            filePath = os.path.join(self.storageDir, msg[1])
            self.safe_print("Client on {0} wants to upload file: {1}".format(clientAddr, filePath))
            if os.path.exists(filePath):
                self.safe_print("!-- File {0} already exists, cannot be uploaded (port {1})".format(filePath, clientAddr))
                clientSock.sendall("!-- File {0} already exists, cannot be uploaded (port {1})".format(filePath, clientAddr).encode())
                clientSock.close()
                return
            with open(filePath, 'wb') as f:
                clientSock.sendall("ok".encode())
                f.write(clientSock.recv(4096))
            

        print("--closing connection {0}--".format(clientSock))
        clientSock.close()
        return




############################################ REDO MAIN FUNCTION FOR BETTER COMMAND LINE FUNCTIONALITY
def main():
    # Create a server
    server = FileServer()
        
    # Start main handler loop
    server.looper()


if __name__ == "__main__":
    main()
