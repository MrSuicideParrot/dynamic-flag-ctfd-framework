from docker import from_env
import logging as log
from secrets import token_hex
from ctfd_api import CTFDClient


def process_challenges(challenges):
    challenges_db = {}

    for i in challenges:
        challenges_db[i["name"]] = [i["id"]]

    return challenges_db


def process_flags(flags):
    flags_db = {}
    for i in flags:
        if i["challenge_id"] in flags_db:
            flags_db["challenge_id"].append(i["id"])
        else:
            flags_db["challenge_id"] = [i["id"]]

    return flags_db


def main():
    ctfd_client = CTFDClient("cenas","http://aaaa")

    challenges = {} #process_challenges(ctfd_client.get_challenges())
    flags_by_challenge = {}#process_flags(ctfd_client.get_flags())

    docker_client = from_env()
    containers = docker_client.containers.list(filters={"label":"dynamic-label=true"})
    for c in containers:
        challenge_name = ""
        flag_localization = ""
        flag_script = ""
        user="root"

        for k, v in c.labels.items():
            if k == "challenge_name":
                challenge_name = v
            elif k == "flag_localization":
                flag_localization = v
            elif k == "flag_script":
                flag_script = v

        if not challenge_name:
            log.warning(f"challenge_name not defined on {c.name}")
            continue

        try:
            challenge_id = challenges[challenge_name]
        except KeyError:
            log.warning(f"Challenge - {challenge_name} - not found ")
            continue

        if not flag_localization and not flag_script:
            log.warning(f"neither flag_localization or flag_script is defined")
            continue

        new_flag = "flag{%s}" % token_hex(16)

        if flag_localization:
            _, s = c.exec_run("/bin/sh -c 'cat >"+flag_localization+"'", stdout=False, stderr=False, stdin=True, socket=True, tty=True)
            s._sock.send(new_flag.encode())
            s._sock.send(b"\n\x04")
            s._sock.close()
            s.close()
        else:
            result, _ = c.exec_run([flag_localization, new_flag])
            if result != 0:
                log.warning(f"Error running command {flag_localization} on {c.name}")
                continue

        ctfd_client.add_flag(challenge_id, new_flag)

        try:
            flags = flags_by_challenge[challenge_id]
            flags.sort()
            ctfd_client.delete_flag(flags[0])
        except KeyError:
            pass


if __name__ == '__main__':
    main()
