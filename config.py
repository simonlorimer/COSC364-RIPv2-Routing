#==============================================================================|
# config.py - config file command-line that acts as a working RIPv2 Router     |
#==============================================================================|
# COSC364 Assignment 1: RIPv2 Protocol                                         |
# Authors: Simon Lorimer (sal180, 34339189), Sean Madondo (sma297, 62519841)   |
#==============================================================================|

#import statements
import socket
import sys
import re
import time
import select
import threading
import pickle

#global constants
UDP_IP = "127.0.0.1"
periodic_update = 10.0 #how often periodic update is sent
invalidate_timer = 20.0 #after this time elapses it will remove
table_update = 5 #how often to update table

class Router:
    """
    Creates a Router that operates under the RIPv2 protocol. 
    
    Attributes:
    router_id = int: Router Identification
    input_ports = [port, port..]: Ports to listen on, which neighbouring routers 
    can access
    outputs = [port, cost, router_id]: a list of neighbouring outgoing Ports, 
    cost metric and router_id 
    
    Methods:
    __init__()
    __str__()
    send_periodic_update()
    send_triggered_update()
    receive()
    
    Please read Router class methods for more detailed descriptions.
    """
    
    def __init__(self, router_id, input_ports, outputs):
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs
        
        self.routing_table = [self.router_id, {}] # {} is a dict which stores key = router_id and value = [port, cost, nexthop]
    
    def __str__(self):
        """ Print the Routing Table of the Router. """       
        string = ('\033[92m'+ "Router ID: " + str(self.router_id) + '\033[0m')   #printing current date and time
        string += "\nDate/Time: " + time.strftime("%d-%m-%y %H:%M:%S")
        string += "\nInput Ports: " + str(self.input_ports)
        string += "\n============= RIPv2 Routing Table ==========="
        string += "\n=Router==|==Port======|==Cost====|==Next-hop=\n"
        for key, value in sorted(self.routing_table[1].items()):
            port, cost, next_hop = value
            if cost == 16:
                string += "{:<8} | {:<10} | {:<8} | {:<10}\n".format(key, port, '*', '-')
            else:
                string += "{:<8} | {:<10} | {:<8} | {:<10}\n".format(key, port, cost, next_hop)
        return string    
        
    def send_periodic_update(self):
        """ Send a Periodic Update to a neighbouring Router. """
        threading.Timer(periodic_update, self.send_periodic_update).start()
        
        for each in self.outputs:
            send_table = {}
            for key, value in self.routing_table[1].items():
                if each[2] != value[2] and key != each[2]:
                    send_table[key] = value
                
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_file = pickle.dumps([self.router_id, send_table] + [1])
            sock.sendto(send_file, (UDP_IP, each[0]))
                
    def send_triggered_update(self, invalid_route):
        """ Send a Triggered Update to a Router, using the invalid_route 
        argument given. """
        for each in self.outputs:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_file = pickle.dumps([self.router_id, invalid_route] + [2])
            sock.sendto(send_file, (UDP_IP, each[0]))                      
        
    def receive(self):
        """Receive a request from a neighbouring Router. """
        #bind socket to input ports, specified IP (default localhost)
        print("Creating socket..")
        
        socket_list = []
        
        try:     
            for each in self.input_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind((UDP_IP, each))
                socket_list.append(sock)
                print("Socket bound to port " + str(each))
            print()
                
        except socket.error as msg:
            print()
            print('>>> Connection Failed. Error Message: ' + str(msg))
            sys.exit()  
        
        else:
            #create time dict for router received
            time_dict = {}            
            
            while True:
                ready_read, _, _ = select.select(socket_list, [], [], table_update)
                print()               
                print(self) #print routing table (itself)
                
                for sock in ready_read:
                    data, clientaddr = sock.recvfrom(1024)
                    received = pickle.loads(data)
                    
                    #received info is in format [router_id, {routing table dict}, message_type]
                    recv_r_id = received[0]
                    routing_table = received[1]
                    message_type = received[2]
                    
                    if message_type == 2: #Request 2: Receiving Triggered Update
                        for key, value in routing_table.items():
                            if key in self.routing_table[1].keys():
                                port = self.routing_table[1][key][0]
                                self.routing_table[1][key] = [port, 16, recv_r_id]                               
                            
                    elif message_type == 1: #Request 1: Receiving Periodic Update
                        for each in self.outputs:
                            if each[2] == recv_r_id:
                                time_dict[recv_r_id] = time.time() # add timer for router received
                                
                                if recv_r_id in self.routing_table[1].keys(): # check this out
                                    if each[1] < self.routing_table[1][recv_r_id][1]: #
                                        self.routing_table[1][recv_r_id] = [each[0], each[1], 'D/A'] #
                                else:
                                    if each[1] < 16:
                                        self.routing_table[1][recv_r_id] = [each[0], each[1], 'D/A']                                    
                                
                                for router, info in routing_table.items():
                                    #same router as this router, do not make any changes
                                    if router == self.router_id:
                                        continue
                                    elif info[1] == 16:
                                        if router in self.routing_table[1].keys():
                                            if self.routing_table[1][router][0] == info[0]:
                                                self.routing_table[1][router] = [info[0], 16, recv_r_id]

                                        #else if router is not currently in table, add
                                    elif router not in self.routing_table[1].keys():
                                        if (each[1] + info[1]) < 16:
                                            self.routing_table[1][router] = [info[0], each[1] + info[1], recv_r_id]
          
                                    #else if router is in table, check to see if path is cheaper, if so then update
                                    elif (each[1] + info[1]) < (self.routing_table[1][router][1]):
                                        self.routing_table[1][router] = [info[0], each[1] + info[1], recv_r_id]
                        
                for router, value in time_dict.items():
                    time_passed = float(time.time() - value)
                    if float(time_passed) > invalidate_timer:
                        #print red
                        print("Router " + str(router) + " time: " + '\033[91m' + str(time_passed) + '\033[0m')                    
                    elif float(time_passed) > periodic_update and float(time_passed) < invalidate_timer:
                        #print yellow
                        print("Router " + str(router) + " time: " + '\33[33m' + str(time_passed) + '\033[0m')
                    else:
                        #print normal
                        print("Router " + str(router) + " time: " + '\033[92m' + str(time_passed) + '\033[0m')
                    if float(time_passed) > invalidate_timer:
                                                     
                        #update routing table
                        before_update = self.routing_table[1][router]
                        self.routing_table[1][router] = [before_update[0], 16, before_update[2]]
                        
                        #any routes that used this router as a hop now get marked as
                        for key, value in self.routing_table[1].items():
                            if value[2] == router:
                                before_next_hop = self.routing_table[1][key]
                                self.routing_table[1][key] = [before_next_hop[0], 16, before_next_hop[2]]
                            
                        #Send Triggered Update
                        invalid_route = {}
                        invalid_route[router] = [before_update[0], 16, before_update[2]]
                        self.send_triggered_update(invalid_route)                                                   
                print()             
        
def check_validity(router_id, input_ports, outputs):
    """ Checks the variables found are within their bounds """
    #check router_id is valid
    if (router_id < 1 or router_id > 64000):
        print("The Router ID " + str(router_id) + " must be between 1 and 64000")
        return False
    
    #check input_ports are valid and have no duplicates
    duplicates = []
    for each in input_ports:
        
        #check number validity
        if (each < 1024 or each > 64000):
            print("The Input Port " + str(each) + " must be between 1024 and 64000")
            return False
        
        #check duplicates
        if each in duplicates:
            print("The Input Port " + str(each) + " can only occur at most once")
            return False
        
        duplicates.append(each)
        
    #check outputs are valid
    duplicates = []
    for each in outputs:
        if (each[0] < 1024 or each[0] > 64000):
            print("The Output Port " + str(each[0]) + " must be between 1024 and 64000")
            return False
        
        if each[0] in duplicates:
            print("The Output Port " + str(each[0]) + " can only ocur at most once")
            return False
        
        duplicates.append(each[0])
        
        if each[2] == router_id:
            print("Output Router ID " + str(each[2]) + " cannot match Router ID")
            return False
        
    #if function passes all checks, return True
    return True

def read_configuration_file(filename):
    """ Opens and reads the configuration file, reading each line for variables.
    returns variables if successful.
    """
    
    #open the file and read
    f = open(filename, "r")
    config_file = f.readlines()
    
    #try to get the router-id, input-ports and outputs from each line
    entry_check = []
    for each in config_file:
        if "#" in each:
            continue
        else:
            
            if "router-id " in each:
                try:
                    router_id = int(each.replace("router-id ", ""))
                    entry_check.append("r_id")
                except ValueError:
                    print("Invalid Router ID entry!\n")
                    sys.exit("Program will now exit.....")
                
            if "input-ports " in each:
                input_ports = [int(s) for s in re.findall(r'\d+', each)]
                if len(input_ports) is 0:
                    print("No Input ports specified!\n")
                    sys.exit("Program will now exit......")
                else:
                    entry_check.append("i_port")
                
            if "outputs " in each:
                outputs = []
                outputs_processing = each.strip("outputs \n").split(", ")
                for each in outputs_processing:
                    outputs.append(each.split("-"))
                for each in outputs:
                    try:
                        each[0], each[1], each[2] = int(each[0]), int(each[1]), int(each[2])
                        entry_check.append("o_port")
                    except ValueError: 
                        print("Invalid output port entry!\n")
                        sys.exit("Program will now exit.....")                        
                    
    if "r_id" not in entry_check:
        print("No router-id given!\n")
        sys.exit("Program will now exit.....")  
    if "i_port" not in entry_check:
        print("No input-ports specified!\n")
        sys.exit("Program will now exit.....")  
    if "o_port" not in entry_check:
        print("No output-ports specified!\n")
        sys.exit("Program will now exit.....") 

    #check data is valid
    if check_validity(router_id, input_ports, outputs):
        print("Validity checks were successful...")
        return router_id, input_ports, outputs
    else:
        print("Validity checks were unsuccessful...\nThe Program will not exit...")
        sys.exit()

def main():
    """ The main function of the program which calls other functions and Router
    class. """
    
    #select router config
    filename = input("Please select the configuration file: ") 
    
    #read config file
    router_id, input_ports, outputs = read_configuration_file(filename)
    
    #create Router
    router = Router(router_id, input_ports, outputs)
    
    #start loop of listening + sending periodic updates
    router.send_periodic_update()
    router.receive()
    
main()