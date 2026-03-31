class AppState:
    def __init__(self):
        self.current_mode = "LOCAL"
        self.server_url = ""
        self.agent_id = ""
        self.server_online = False
        self.last_heartbeat = "-"
        self.last_register = "-"
        self.last_error = ""
        self.current_job = "-"


app_state = AppState()