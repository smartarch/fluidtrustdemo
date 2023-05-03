from components import CustomsAgent, LeadCustomsAgent, Component
from helpers import Statistics

import logging


def too_lazy_agent(agent: CustomsAgent, statistics: Statistics) -> bool:
    virtually = statistics.agent_virtually_inspected(agent.identification)
    physically = statistics.agent_physically_inspected(agent.identification)
    both = virtually + physically
    return virtually / both > 0.3 if both > 10 else False


class CustomsAgentTooLazyRule:

    def __init__(self, lead_agent: LeadCustomsAgent, statistics, all_components: list[Component]):
        self.statistics = statistics
        self.all_components = all_components
        self.instantiated_rules = []
        self.lead_agent = lead_agent
        self.agent = None

    def condition(self, agent: CustomsAgent) -> bool:
        if too_lazy_agent(agent, self.statistics) and agent not in self.lead_agent.agents_inspected():
            return True
        return False

    def actuate(self):
        self.lead_agent.inspect_lazy_agent(self.agent)

    def __condition(self) -> bool:
        return self.condition(self.agent)

    def __active_agent(self):
        return self.agent

    def evaluate(self):
        for component in self.all_components:
            if isinstance(component, CustomsAgent):
                if self.condition(component):
                    found = False
                    for rule in self.instantiated_rules:
                        if rule.__active_agent() is component:
                            found = True
                            break
                    if not found:
                        r = CustomsAgentTooLazyRule(self.lead_agent, self.statistics, self.all_components)
                        r.agent = component
                        logging.info(f'CustomsAgentTooLazyRule instantiated for {component.identification} -- it has ')
                        self.instantiated_rules.append(r)
        # actuate instantiated rules
        for rule in self.instantiated_rules:
            rule.actuate()
        # remove inactive rules
        for rule in list(self.instantiated_rules):
            if not rule.__condition():
                self.instantiated_rules.remove(rule)
                logging.info(f'CustomsAgentTooLazyRule removed for {rule.__active_agent().identification}')
