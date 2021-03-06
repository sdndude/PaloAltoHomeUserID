# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

import urllib
import urllib.request
import urllib.parse
import sys
import ssl
import xml.etree.ElementTree as ET
import pymysql
import time
from datetime import datetime


try:
    from variables import *
except ImportError:
    for arg in sys.argv: 1
# use the command line to call the function from a single script.
    if arg == "setup":
        print ("")
    else:
        print ("Run dhcpuserid.py setup")
        sys.exit(0)
        

    
def Createvariables(): 

    Host = input("Enter the IP or host name of the Firewall: ")
    Admin = input("Enter the admin username: ")
    Password = input("Enter the admin password: ")

    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE

    url = "https://%s/api/?type=keygen&user=%s&password=%s" %(Host,Admin,Password)
    req = urllib.request.Request(url, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result = resp_str.read()
    tree = ET.fromstring(result)
    for child in tree.iter('key'):
        apikey = child.text

    key = "key = '%s' \n" %(apikey)
    base = "base ='https://%s/api/'\n" %(Host)

    dbHost = input("Enter the IP or host name of the Mysql Server: ")
    dbHost = "host = '%s' \n" %(dbHost)
    dbPort = input("Enter the port number for the Mysql Server: ")
    dbPort = "port = %s \n" %(dbPort)
    dbUser = input("Enter the admin user for the Mysql Server: ")
    dbUser = "user = '%s' \n" %(dbUser)
    dbPass = input("Enter the admin password for the Mysql Server: ")
    dbPass = "passwd = '%s' \n" %(dbPass)
    dbDb = input("Enter the name of the database: ")
    dbDb = "db = '%s' \n" %(dbDb)
    
    
    interface = input("Enter the full name of the interface you want the DHCP data imported from e.g. ethernet1/2, ethernet1/2.2, all:")
    interface = "interface = '%s' \n" %(interface)
    
    resp_str.close
    f = open('variables.py', 'w')
    f.write(key)
    f.write(base)
    f.write(dbHost)
    f.write(dbPort)
    f.write(dbUser)
    f.write(dbPass)
    f.write(dbDb)
    f.write(interface)
    f.close()
    
    print ("\n\nvariables written to file")
 
 
def dbsetup():
     
    conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
    state = """ CREATE TABLE `DHCP` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `MacAddr` varchar(20) NOT NULL,
  `Vendor` varchar(50) DEFAULT NULL,
  `IPaddr` decimal(11,0) DEFAULT NULL,
  `Hostname` varchar(50) DEFAULT NULL,
  `DisplayName` varchar(50) DEFAULT NULL,
  `LeaseTime` datetime DEFAULT NULL,
  `Source` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`UID`),
  UNIQUE KEY `MacAddr_UNIQUE` (`MacAddr`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;"""
    
    cur = conn.cursor()
    cur.execute(state)
    cur.close()
    
    state1 = """ CREATE TABLE `GROUPS` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `GName` varchar(50) DEFAULT NULL,
  `Desc` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`UID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1; """
    
    cur1 = conn.cursor()
    cur1.execute(state1)
    cur1.close()
    
    state2 = """CREATE TABLE `Group_User_Map` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `DHCP_UID` int(11) DEFAULT NULL,
  `Group_UID` int(11) DEFAULT NULL,
  PRIMARY KEY (`UID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;"""
    
    cur2 = conn.cursor()
    cur2.execute(state2)
    cur2.close()
        
    conn.commit() 
    conn.close()  

def collectdhcp(): 
    
 # 
    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE
    conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
    
    typeop = "op"
    cmd = "<show><dhcp><server><lease><interface>%s</interface></lease></server></dhcp></show>" %(interface)
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
#    print (cmd1)
    req = urllib.request.Request(cmd1, data=None )
#    req.add_header( 'key', key )
#    req.add_header( 'type', typeop )
#    req.add_header( 'cmd', cmd )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result = resp_str.read()
    print (result)
    tree = ET.fromstring(result)
    for child in tree.iter('entry'):
        ip = child.find('ip').text
        
        mac =  child.find('mac')
        if mac is None:
            mac = 'blank'
        else:
             mac =  child.find('mac').text
             
        hostname =  child.find('hostname')
        if hostname is None:
            hostname = 'blank'
        else:
             hostname =  child.find('hostname').text

        
        name = child.get('name')
        leasetime = child.find('leasetime')
        if leasetime is None:
            leasetime = 'Jan  1 00:00:01 1970'
            leasetime = datetime.strptime(leasetime, '%b %d %H:%M:%S %Y')
            
        else:
            leasetime =  child.find('leasetime').text
            leaselen = len(leasetime)
            leasetime = leasetime[:leaselen-1]
            leasetime = datetime.strptime(leasetime, '%a %b %d %H:%M:%S %Y')
        
#        print(ip, mac,  hostname, leasetime )
        state = ("insert into DHCP (IPaddr, MacAddr, Hostname, Leasetime , Source) values (INET_ATON('%s'),'%s','%s','%s' , 'FW' ) ON DUPLICATE KEY UPDATE IPaddr=INET_ATON('%s'), Hostname='%s' , Leasetime='%s' ;") %(ip, mac,  hostname, leasetime, ip,  hostname, leasetime)

        cur = conn.cursor()
        cur.execute(state)
        cur.close()
#        conn.commit() 

    state2 = ("SELECT MacAddr FROM DHCP where `source`= 'FW' and Vendor is null;")

    cur2 = conn.cursor()
    cur2.execute(state2)
    results2 = cur2.fetchall()

    for row in results2: 
        mac = row[0]
#            print (mac)

        myssl = ssl.create_default_context();
        myssl.check_hostname=False
        myssl.verify_mode=ssl.CERT_NONE
        url = "https://api.macvendors.com/%s" %(mac)
        req = urllib.request.Request(url, data=None )
        try :
            resp_str = urllib.request.urlopen(req ,context=myssl)
            result3 = resp_str.read().decode('utf-8')
            result3 = result3.replace('\uff0c', '')

            print(mac ,' = ' , result3 )            
        except urllib.error.HTTPError as error:
            print(error.code)
            result3 = 'Unknown'
#            print(mac ,' = ' , result3 )
        cur3 = conn.cursor()
        state3 = ("UPDATE DHCP set vendor = \"%s\" where MacAddr = \"%s\";") %(result3, mac)
        cur3.execute(state3)
        cur3.close()
#        print(mac ,' + ' , result3 )
        time.sleep(1)




#            conn.commit() 

        cur2.close()
        conn.commit()         
        
    conn.close()   
        

def CreateXMLFile(): 

    root = ET.Element("uid-message")
    ET.SubElement(root, "type").text = "update"
    payload = ET.SubElement(root, "payload")

    login = ET.SubElement(payload, "login")    
 
    conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
    state = ("Select IFNULL(DisplayName, Hostname), INET_NTOA(IPaddr)  from DHCP where (Hostname <> 'blank' or DisplayName is not null) and LeaseTime in ( select MAX(LeaseTime)  from DHCP group by IPaddr desc) order by IPaddr;")
    cur = conn.cursor()
    cur.execute(state)
    results = cur.fetchall()
    for row in results: 
        Name = row[0]
        IP = row[1]
        ET.SubElement(login, "entry", name=Name , ip=IP )
        #    print(Name , IP)
       
    cur.close()
    groups = ET.SubElement(payload, "groups")  
     
    state1 = ("select GName from GROUPS;")
    # "SELECT ifnull(DHCP.DisplayName,DHCP.Hostname) FROM DHCP where UID in (select Group_User_Map.DHCP_UID from Group_User_Map where Group_User_Map.Group_UID = (select UID from `Group` where `Group`.`Group`= 'admin'))")
    cur1 = conn.cursor()
    cur1.execute(state1)
    results1 = cur1.fetchall()
    for row in results1: 
        Group = row[0]
   #     print (Group)
        group = ET.SubElement(groups, "entry", name=Group )
        state2 = ("SELECT distinct(ifnull(DHCP.DisplayName,DHCP.Hostname)) FROM DHCP where UID in (select Group_User_Map.DHCP_UID from Group_User_Map where Group_User_Map.Group_UID = (select UID from GROUPS where GName= '%s'))") %(Group)
        cur2 = conn.cursor()
        cur2.execute(state2)
        results2 = cur2.fetchall()
        members = ET.SubElement(group , "members") 
        for row in results2: 
            Member = row[0]
  #          print (Member)
            ET.SubElement(members, "entry", name=Member )
        
        #    print(Name , IP)
    
    cur2.close()
    cur1.close()

    conn.close() 
    
    
    tree = ET.ElementTree(root)
    tree.write("userID.xml")

    
def SendAPI(): 

    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE
    


    fileN = open('userID.xml', 'r')
    # xml convert the file to a single URL #
    xml = urllib.parse.quote_plus(fileN.read())
    typeop = "user-id"
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,xml)
#    print (cmd1)
    req = urllib.request.Request(cmd1, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result = resp_str.read()
    print (result)
    
    
    
    
def userguide():   
    
    print (" The following is the user guide for the tool")
    print (" --------------------------------------------")
    print (" see readme.md")
    
    

if __name__ == '__main__':
    
    for arg in sys.argv: 1
# use the command line to call the function from a single script.
    if arg == "help":
        userguide()
    elif arg == "setup":
        Createvariables()
    elif arg == "dbsetup":
        dbsetup()
    elif arg == "dhcp":
        collectdhcp()
    elif arg == "xml":
        CreateXMLFile()
    elif arg == "update":
        SendAPI()
    elif arg == "run":
        collectdhcp()
        CreateXMLFile()
        SendAPI()
    else:
        collectdhcp()
#        CreateXMLFile()
#        SendAPI()