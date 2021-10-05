import asyncio
from concurrent.futures.process import ProcessPoolExecutor

from fastapi import FastAPI
from docker import from_env
import logging as log
from secrets import token_hex

from ctfd_api import CTFDClient
from os import getenv

scheduler = None
log.basicConfig(level=log.INFO)

ctfd_client = None
docker_client = None

app = FastAPI()

docker_client = from_env()

keys = ["CTFD_URL", "TOKEN"]
config = {}

for i in keys:
    resul = getenv(i)
    if resul is None:
        log.fatal(i + " isn't defined!")
        exit(1)
    else:
        config[i] = resul

ctfd_client = CTFDClient(config["TOKEN"], config["CTFD_URL"])

def process_challenges(challenges):
    challenges_db = {}

    for i in challenges:
        challenges_db[i["name"]] = i["id"]

    return challenges_db


def process_flags(flags):
    flags_db = {}
    for i in flags:
        if i["challenge_id"] in flags_db.keys():
            flags_db[i["challenge_id"]].append(i["id"])
        else:
            flags_db[i["challenge_id"]] = [i["id"]]

    return flags_db

def search_for_new_containers():
    while True:
        evs = docker_client.events(decode=True)
        for ev in evs:
            try:
                if ev[u'status'] == u'start':
                    cont = docker_client.containers.get(ev[u'id'])
                    if cont.labels["dynamic-label"]:
                        log.info(f"Container was started - {cont.name}")
                        deploy_container(cont)
            except KeyError:
                pass

def deploy_container(c):
    challenges = process_challenges(ctfd_client.get_challenges())
    flags_by_challenge = process_flags(ctfd_client.get_flags())

    challenge_name = ""
    flag_localization = ""
    flag_script = ""
    user = "root"

    for k, v in c.labels.items():
        if k == "challenge-name":
            challenge_name = v
        elif k == "flag-localization":
            flag_localization = v
        elif k == "flag-script":
            flag_script = v

    if not challenge_name:
        log.warning(f"challenge_name not defined on {c.name}")
        return

    try:
        challenge_id = challenges[challenge_name]
    except KeyError:
        log.warning(f"Challenge - {challenge_name} - not found ")
        return

    if not flag_localization and not flag_script:
        log.warning(f"neither flag_localization or flag_script is defined")
        return

    new_flag = "flag{%s}" % token_hex(16)

    if flag_localization:
        _, s = c.exec_run("/bin/sh -c 'cat >" + flag_localization + "'", stdout=False, stderr=False, stdin=True,
                          socket=True, tty=True)
        s._sock.send(new_flag.encode())
        s._sock.send(b"\n\x04")
        s._sock.close()
        s.close()
    else:
        result, _ = c.exec_run([flag_localization, new_flag])
        if result != 0:
            log.warning(f"Error running command {flag_localization} on {c.name}")
            return

    ctfd_client.add_flag(challenge_id, new_flag)

    try:
        flags = flags_by_challenge[challenge_id]
        if len(flags) > 0:  # this is to ensure there are one flag
            flags.sort()
            ctfd_client.delete_flag(flags[0])
    except KeyError:
        pass

    log.info(f"Challenge flag from {challenge_name} was updated.")

def initialize_containers():
    log.info("Initializing running containers.")
    docker_client = from_env()
    containers = docker_client.containers.list(filters={"label": "dynamic-label=true"})
    for c in containers:
        deploy_container(c)


@app.post("/solve/{challenge_id}")
async def change_flag(challenge_id: int):
    challenges = process_challenges(ctfd_client.get_challenges())
    for k, v in challenges.items():
        if v == challenge_id:
            containers = docker_client.containers.list(filters={"label": ["dynamic-label=true",
                                                                          f"challenge-name={k}"]})

            if len(containers) == 0:
                log.warning(f"I - Container not found - {k}.")

            if len(containers) > 1:
                log.warning("More than one container was returned.")

            deploy_container(containers[0])
            return {"status": "ok"}

    log.warning(f"O - Container not found - {challenge_id}.")
    return {"status": "container not found."}


@app.on_event("startup")
async def on_startup():
    app.state.executor = ProcessPoolExecutor()
    loop = asyncio.get_event_loop()
    loop.run_in_executor(app.state.executor, search_for_new_containers)


@app.on_event("shutdown")
async def on_shutdown():
    app.state.executor.shutwdown()

initialize_containers()

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
