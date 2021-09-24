from requests import Session


class CTFDClient:
    def __init__(self, token, base):
        self.base = base
        self.session = Session()
        self.session.headers.update({"Authorization": f"Token {token}"})

    def _get(self, endpoint):
        return self.session.get(self.base + endpoint,json="")

    def get_challenges(self):
        resp = self._get("/challenges")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_flags(self):
        resp = self._get("/flags")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_flag(self, flag_id):
        resp = self._get(f"/flags/{flag_id}")
        resp.raise_for_status()
        return resp.json()["data"]

    def delete_flag(self, flag_id):
        self.session.delete(self.base + f"/flags/{flag_id}").raise_for_status()

    def add_flag(self, challenge_id, flag, type="static", case_sensitive=True):
        data = {
            "challenge_id": challenge_id,
            "content": flag,
            "type": type,
            "data": "case_insensitive" if not case_sensitive else "case_sensitive"
        }

        self.session.post(self.base + "/flags", json=data).raise_for_status()
