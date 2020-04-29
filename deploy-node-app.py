#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import signal
import socket
import sys

import git
import requests


# HELP
####################################################################################
def help():
    print(sys.argv[0])
    print("deploy a node app (to run server side)")
    print("-"*100)
    print("Usage : "+sys.argv[0] +
          " [-h|--help] [-f|--folder] <app_folder> [-c|--conf] <conf_file> [-p|--pull] [-i|--install] [-a|--auto] [-s|--stop] [-k|--kill]\n")
    print("  *  -f|--folder     : [mandatory]  node application path\n")
    print("  *  -c|--conf       : conf path\n")
    print("  *  -p|--pull       : git pull before launch\n")
    print("  *  -i|--install    : install before launch\n")
    print("  *  -a|--auto       : git pull and install if diff with origin branch\n")
    print("  *  -s|--stop       : stop app\n")
    print("  *  -k|--kill       : kill app\n")
    print("  *  -h|--help       : display this help\n")

    print("ex : {script} -f {f} -c deploy-conf.json --auto".format(
        script=sys.argv[0],
        f="/home/dave/bitch"))
    print("-"*100)
    exit(0)


# CLASS WEBHOOK
####################################################################################
class Webhook:
    url = None
    username = ''
    host_url = ''

    def __init__(self, url):
        self.url = url

    def send(self, message):
        if self.url:
            title = message

            data = {}
            data["username"] = self.username

            data["embeds"] = []
            embed = {}
            embed["title"] = title
            embed["url"] = self.host_url
            data["embeds"].append(embed)

            result = requests.post(self.url, data=json.dumps(data), headers={
                "Content-Type": "application/json"})

            try:
                result.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(err)
            else:
                print("Webhook delivered successfully, code {}.".format(
                    result.status_code))
        else:
            print("! Webhook has no url")


# GET PARAMETERS
####################################################################################
def get_params():
    """
        get input param:
            - app_folder
            - conf_file
            - do_install
            - do_pull
            - do_auto
            - do_stop
            - do_kill
    """

    # case help
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) == 1:
        help()
        exit(1)

    # check mandatory
    if not '-f' in sys.argv and not '--folder' in sys.argv:
        print("!! missing folder parameter")
        exit(1)

    # init params
    app_folder = None
    conf_file = None
    do_pull = False
    do_install = False
    do_auto = False
    do_stop = False
    do_kill = False

    # parse arguments (app_folder)
    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-f' or sys.argv[i] == '--folder':
            try:
                app_folder = os.path.realpath(sys.argv[i+1])
            except IndexError:
                print("! bad app folder parameter")
                exit(1)
            if not os.path.exists(app_folder):
                print("! app doesn't exists")
                # exit(1)
        if sys.argv[i] == '-c' or sys.argv[i] == '--conf':
            try:
                conf_file = os.path.realpath(sys.argv[i+1])
            except IndexError:
                print("! bad conf file parameter")
                conf_file = None
        if sys.argv[i] == '-p' or sys.argv[i] == '--pull':
            do_pull = True
        if sys.argv[i] == '-i' or sys.argv[i] == '--install':
            do_install = True
        if sys.argv[i] == '-a' or sys.argv[i] == '--auto':
            do_auto = True
        if sys.argv[i] == '-s' or sys.argv[i] == '--stop':
            do_stop = True
        if sys.argv[i] == '-k' or sys.argv[i] == '--kill':
            do_kill = True

    return app_folder, conf_file, do_pull, do_install, do_auto, do_stop, do_kill


# GET CONF
####################################################################################
def get_conf(conf_file):
    if not conf_file or not os.path.exists(conf_file):
        return None

    try:
        f = open(conf_file, 'r')
    except IOError:
        print("! bad conf file")
        return None

    return json.load(f)


# PARSE CONF
###################################################################################
def parse_conf(json_conf):
    env = ''
    webhook = None

    # parse env
    for var in json_conf['env']:
        env += ("{}='{}' ").format(var['name'], var['value'])

    # parse webhook
    if 'webhook' in json_conf:
        if 'url' in json_conf['webhook']:
            webhook = Webhook(json_conf['webhook']['url'])
        if 'username' in json_conf['webhook']:
            webhook.username = json_conf['webhook']['username']
        if 'host_url' in json_conf['webhook']:
            webhook.host_url = json_conf['webhook']['host_url']

    return env, webhook


# RUN CMD
####################################################################################
def run_cmd(cmd):
    print("--> {}".format(cmd))
    try:
        if os.system(cmd) != 0:
            raise Exception('wrong command !')
            exit(1)
    except:
        print("\n{}: command failed !".format(cmd))
        exit(1)


# FIND PROCESS
####################################################################################
def find_process(app_folder):
    print('looking for app process ...')
    app_pid = None

    # get list of all pids
    all_pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

    # looking for proc with cmd 'node index.js' runned from app_folder
    for pid in all_pids:
        try:
            f = open(os.path.join('/proc', pid, 'cmdline'), 'rt')
            cmd = f.read().split('\0')

            if cmd[0] == "node" and cmd[1] == "index.js":
                # found proc with cmd 'node index.js'
                node_proc_folder = os.path.realpath(
                    os.path.join('/proc', pid, 'cwd'))

                if node_proc_folder == app_folder:
                    # found proc runned from app_folder
                    app_pid = pid
                    break

        except IOError:  # proc has already terminated
            continue

    return app_pid


####################################################################################
####################################################################################
# MAIN
####################################################################################
if __name__ == "__main__":

    # get params
    app_folder, conf_file, do_pull, do_install, do_auto, do_stop, do_kill = get_params()

    # get json conf
    json_conf = get_conf(conf_file)
    env, webhook = parse_conf(json_conf)
    webhook_start_message = None
    webhook_stop_message = None
    if 'webhook' in json_conf and 'start_message' in json_conf['webhook']:
        webhook_start_message = json_conf['webhook']['start_message']

    if 'webhook' in json_conf and 'stop_message' in json_conf['webhook']:
        webhook_stop_message = json_conf['webhook']['stop_message']

    if do_stop or do_kill:
        # STOP OR KILL APP
        ##########################################
        app_pid = find_process(app_folder)

        # if process has been found : KILL IT !
        if app_pid:
            print('matching process found, pid = {}'.format(app_pid))

            try:
                if do_kill:
                    os.kill(int(app_pid), signal.SIGKILL)
                    print('killed <3')
                elif do_stop:
                    os.kill(int(app_pid), signal.SIGTERM)
                    print('stopped ;)')
                if webhook:
                    webhook.send(webhook_stop_message)
            except:
                print('! failed to stop / kill app')
        else:
            print('no matching process found')
        ##########################################

    if do_auto or do_pull:
        # SET REPO VARIABLE
        ##########################################
        repo = git.Repo(app_folder)
        ##########################################

    if do_auto:
        # CHECK FOR DIFF WITH ORIGIN - FORCE PULL AND INSTALL
        ##########################################
        do_pull = False
        do_install = False

        # fetch origin
        print("git fetch origin ...")
        repo.remotes.origin.fetch()

        # diff between local local and origin branches
        commit_master = repo.commit("master")
        commit_origin_master = repo.commit("origin/master")
        diff = commit_origin_master.diff(commit_master)

        if diff:
            print("Found diff with origin")
            do_pull = True
            do_install = True
        else:
            print("No diff with origin found")
        ##########################################

    if do_pull:
        # PULL ORIGIN
        ##########################################
        print("force exact same state as origin ...")
        # blast any current changes
        repo.git.reset('--hard', 'origin/master')
        # ensure master is checked out
        repo.heads.master.checkout()
        # blast any changes there (only if it wasn't checked out)
        repo.git.reset('--hard', 'origin/master')
        # remove any extra non-tracked files (.pyc, etc)
        repo.git.clean('-xdf')
        # pull in the changes from from the remote
        repo.remotes.origin.pull('--force')
        # TODO: git submodule update --recursive --remote
        ##########################################

    if do_install:
        # INSTALL AND BUILD
        ##########################################
        print("npm install ...")
        os.chdir(app_folder)
        run_cmd('npm install')
        # TODO: specific ...
        run_cmd(
            'npm install --prefix {f} && npm run build --prefix {f}'.format(f='client'))
        ##########################################

    if not do_stop:
        # SET ENV VARIABLES & START APP
        ##########################################
        print("\n\nAPP STARTING _________________________________\n")
        os.chdir(app_folder)
        # TODO: specific ...
        run_cmd('{e} npm run start &'.format(e=env))
        if webhook:
            webhook.send(webhook_start_message)
        ##########################################
