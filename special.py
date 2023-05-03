#!/usr/bin/env python3

from components import CustomsAgent


class LazyCustomsAgent(CustomsAgent):
    def __init__(self,  identification: str, home_position: (int, int), statistics):
        super().__init__(identification, home_position, statistics)
        self.punished = False

    def decide_to_proper_check(self) -> bool:
        if not self.punished:
            return False
        else:
            return super().decide_to_proper_check()

    def punish(self):
        self.punished = True
