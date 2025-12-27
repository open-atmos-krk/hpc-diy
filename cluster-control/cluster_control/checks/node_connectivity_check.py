from cluster_control.checks.check import Check

class NodeConnectivityCheck(Check):
    def check(self):
        return True

    def get_name(self):
        return "node connectivity check"
