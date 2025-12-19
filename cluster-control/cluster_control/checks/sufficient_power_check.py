from cluster_control.checks.check import Check

from contextlib import redirect_stdout
import io

from pemmican import cli

class SufficientPowerCheck(Check):
    
    def check(self,):
        f = io.StringIO()

        with redirect_stdout(f):
            cli.main()

        return "This power supply is not capable of supplying 5A;" not in f.getvalue()


    def get_name(self,):
        return "sufficient power check"