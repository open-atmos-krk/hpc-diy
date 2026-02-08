from cluster_control.checks.check import Check

class NodeConnectivityCheck(Check):
    def check(self):
        #TODO: https://github.com/open-atmos-krk/hpc-diy/issues/40
        return True

    def get_name(self):
        return "node connectivity check"
