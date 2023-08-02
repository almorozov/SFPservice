import requests
import random
from datetime import date
from bs4 import BeautifulSoup
from checklib import *


PORT = 7000
spilot = [['Yoda','MWY2YTY0Mzc5'],['Luke','ODU1ODFiNjM3'],['Leia','MWZhZDdmMTkw'],['Han','MWNmYTNhYjcz'],['Ben','ODc0YzgwMjcy'],['Boba','OGYwMTg1ZjM0'],['Lando','OTNjZTc3OTZk'],['Anakin','MDg4NmM0Yjdk'],['Windu','YzZiNDI4NTY1'],['Ren','YjI4ZDYxZTA1']]
splanet = ['Ando','Corellia','Coruscant','Endor','Geonosis','Jakku','Kamino','Kessel','Mustafar','Naboo']

def f_user_reg(host, i):
    rdata = {"login":spilot[i][0], "password":spilot[i][1]}
    url = f'http://{host}:{PORT}/reg'
    r = requests.post(url, data=rdata, timeout=2)
    if r.status_code != 200: return False
    return True
    #print("User_Reg %s", r)

def f_user_login(host, i):
    s = requests.Session()
    rdata = {"login":spilot[i][0], "password":spilot[i][1]}
    url = f'http://{host}:{PORT}/login'
    #print(url)
    r = s.post(url, data=rdata, timeout=2)
    if r.status_code != 200:
        s = False
    ustatus = r.text.find('Login or password incorrect')
    if ustatus > 0:
        s = False
    return s

def f_user_logout(host, s):
    url = f'http://{host}:{PORT}/logout'
    #print(url)
    r = s.get(url, timeout=2)
    if r.status_code != 200: return False
    return True

class CheckMachine:

    def __init__(self, checker):
        self.checker = checker

    def ping(self):
        r = requests.get(f'http://{self.checker.host}:{PORT}/StatusPilotList', timeout=2)
        self.checker.check_response(r, 'Check failed')

    def put_flag(self, flag, vuln):
        new_id = "Zvezda-" + rnd_string(10)
        ipteam = self.checker.host.split(".")
        nteam = int(ipteam[2])
        if nteam > 9: nteam = 0
        s = f_user_login(self.checker.host, nteam)
        if not s:
            fres = f_user_reg(self.checker.host, nteam)
            if not fres:
                self.checker.cquit(Status.MUMBLE, 'Services not working correctly', 'Services not working correctly in put_flag')
            s = f_user_login(self.checker.host, nteam)
            if not s:
                self.checker.cquit(Status.MUMBLE, 'Services not working correctly', 'Services not working correctly in put_flag')
        n = random.randint(0, 9)
        ddate = date.fromisoformat("2033-05-18")
        rdata = {"destination":splanet[n], "depdate":ddate, "starship_name":new_id, "starship_reg":flag, "rem":"//Generate from SFP_Checker"}
        url = f'http://{self.checker.host}:{PORT}/CreateTicket'
        #print(url)
        r = s.post(url, data=rdata, timeout=2)
        self.checker.check_response(r, 'Could not put flag')
        fres = f_user_logout(self.checker.host, s)
        if not fres:
                self.checker.cquit(Status.MUMBLE, 'Services not working correctly', 'Services not working correctly in put_flag')
        return new_id

    def get_flag(self, flag_id, vuln):
        ipteam = self.checker.host.split(".")
        nteam = int(ipteam[2])
        if nteam > 9: nteam = 0
        s = f_user_login(self.checker.host, nteam)
        if not s:
            self.checker.cquit(Status.MUMBLE, 'Services not working correctly', 'Services not working correctly in get_flag')
        url = f'http://{self.checker.host}:{PORT}/search?search='+flag_id
        #print(url)
        r = s.get(url, timeout=2)
        #print(r.status_code)
        if r.status_code != 200:
            self.checker.cquit(Status.MUMBLE, 'Services not working correctly', 'Services not working correctly in get_flag')
        #self.checker.check_response(r, 'Could not get flag')
        data = self.checker.get_text(r, 'Invalid response from /get/')
        sp = BeautifulSoup(data, features="html.parser")
        #tables = sp.find_all('table')
        table = sp.find('table', class_='table-striped')
        for row in table.tbody.find_all('tr'):
            columns = row.find_all('td')
            if(columns != []):
                #print("TD=" + columns[2].text.strip())
                if columns[2].text.strip() == flag_id:
                    rflag = columns[3].text.strip()
                else:
                    rflag = "NotFlag"
        return rflag
