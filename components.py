#!/usr/bin/env python3

from enum import Enum
from dataclasses import dataclass
from random import getrandbits
import logging
from shapely.geometry import LineString
from analysis import execute_analysis


@dataclass(frozen=True)
class Item:
    kind: str
    amount: int
    is_dangerous: bool
    description: str
    price: int


ListOfItems = list[Item]


@dataclass(frozen=True)
class Declaration:
    items: ListOfItems
    source: str
    destination: str
    declared_tax: int

    def has_dangerous(self) -> bool:
        for item in self.items:
            if item.is_dangerous:
                return True
        return False


class ContainerState(Enum):
    DELIVERED = 0
    CLEARED = 1
    UNCLEARED = 2


class Component:
    def __init__(self, identification: str):
        super().__init__()
        self.__identification = identification

    @property
    def identification(self) -> str:
        return self.__identification

    def step(self):
        pass


class Component2D(Component):
    def __init__(self, identification: str):
        super().__init__(identification)
        self.__pos_x = 0
        self.__pos_y = 0

    @property
    def pos_x(self) -> int:
        return self.__pos_x

    @pos_x.setter
    def pos_x(self, x: int):
        self.__pos_x = x

    @property
    def pos_y(self) -> int:
        return self.__pos_y

    @pos_y.setter
    def pos_y(self, y: int):
        self.__pos_y = y

    @property
    def position(self) -> (int, int):
        return self.__pos_x, self.__pos_y


class Container(Component2D):
    def __init__(self, identification: str, company: str, items: ListOfItems, tax: int, declaration: Declaration, state: ContainerState = ContainerState.DELIVERED):
        super().__init__(identification)
        self._company = company
        self._items = items
        self._declaration = declaration
        self._state = state
        self._actual_tax = tax
        self._dangerous = False
        self._cleared_by_customs = ContainerState.DELIVERED
        self._cleared_by_pa = ContainerState.DELIVERED
        for item in self._declaration.items:
            if item.is_dangerous:
                self._dangerous = True
                break

    @property
    def company(self) -> str:
        return self._company

    @property
    def items(self) -> ListOfItems:
        return self._items

    @property
    def tax(self) -> int:
        return self._actual_tax

    @property
    def declaration(self) -> Declaration:
        return self._declaration

    @property
    def state(self) -> ContainerState:
        return self._state

    @state.setter
    def state(self, st: ContainerState):
        self._state = st

    @property
    def dangerous(self) -> bool:
        return self._dangerous

    @property
    def cleared_by_customs(self) -> ContainerState:
        return self._cleared_by_customs

    @cleared_by_customs.setter
    def cleared_by_customs(self, state: ContainerState):
        self._cleared_by_customs = state

    @property
    def cleared_by_pa(self) -> ContainerState:
        return self._cleared_by_pa

    @cleared_by_pa.setter
    def cleared_by_pa(self, state: ContainerState):
        self._cleared_by_pa = state


class AgentState(Enum):
    IDLE = 0
    CHECK = 1
    INSPECTION = 2
    RETURNING = 3
    A_WAITING_PA = 4
    PA_REQUEST_A = 5
    PA_CHECK_WITH_A = 6
    PA_MOVING_TO_A = 7
    PA_DETAILED_CHECK = 8


class Agent(Component2D):
    def __init__(self,  identification: str, home_position: (int, int), statistics):
        super().__init__(identification)
        self._state = AgentState.IDLE
        self._home_position = home_position
        self._target_position = home_position
        self.pos_x = home_position[0]
        self.pos_y = home_position[1]
        self._in_current_state = 0
        self._container = None
        self.statistics = statistics
        self.under_inspection = False

    @property
    def state(self) -> AgentState:
        return self._state

    def step(self):
        pass

    @property
    def home_position(self) -> (int, int):
        return self._home_position

    def punish(self):
        pass


class CustomsAgent(Agent):
    CHECK_DUR = 2
    INSPECTION_DUR = 2
    SPEED = 50
    TRESHOLD_COUNTRY_ERROR_RATE_FOR_INSPECTION = 0.1
    TRESHOLD_COMPANY_ERROR_RATE_FOR_INSPECTION = 0.1
    THRESHOLD_LAST_TAX_DIFFERENCE = 50  # in percents

    def __init__(self,  identification: str, home_position: (int, int), statistics):
        super().__init__(identification, home_position, statistics)

    def assign_container(self, container: Container):
        self._container = container
        self._state = AgentState.CHECK
        self._in_current_state = 0

    def decide_to_proper_check(self) -> bool:
        if execute_analysis("VirtualInspection", "incidentRate", str(self.statistics.country_error_rate(self._container.declaration.source))):
            logging.info('%s discovers too high error rate (or unknown) for a source country of %s', self.identification, self._container.identification)
            return True
        if self.statistics.company_error_rate(self._container.company) >= CustomsAgent.TRESHOLD_COMPANY_ERROR_RATE_FOR_INSPECTION:
            logging.info('%s discovers too high error rate (or unknown) for a shipping company of %s', self.identification, self._container.identification)
            return True
        if execute_analysis("Tax", "tax", str(self._container.declaration.declared_tax / self.statistics.company_last_tax(self._container.company))):
            logging.info('%s discovers too big difference from the last declared tax of the same company of %s', self.identification, self._container.identification)
            return True
        # for the rest of containers, throw a die to decide
        return not getrandbits(2)

    def inspect_container(self) -> bool:
        """Compares that items in the container are the same as the items in the container declaration"""
        return set(self._container.declaration.items) == set(self._container.items)

    def inspect_tax(self) -> bool:
        return self._container.declaration.declared_tax == self._container.tax

    def set_container_position(self, position):
        self._target_position = position

    def is_at_container(self) -> bool:
        return (self._target_position == self.position) and (self._state == AgentState.INSPECTION)

    def ask_inspection(self, container: Container):
        """Called by PA to ask the agent to go for physical inspection"""
        self._state = AgentState.INSPECTION
        self._container = container
        self.statistics.report_agent_physically_inspected(self.identification)
        pass

    def wait_for_pa(self):
        self._state = AgentState.A_WAITING_PA

    def reset_after_pa(self):
        self._state = AgentState.IDLE
        self._container = None
        self._target_position = None

    def step(self):
        if self._state == AgentState.IDLE:
            logging.info('%s does nothing', self.identification)
            pass
        elif self._state == AgentState.CHECK:
            self._in_current_state += 1
            logging.info('%s evaluates %s', self.identification, self._container.identification)
            if self._in_current_state == CustomsAgent.CHECK_DUR:
                self._in_current_state = 0
                if self.decide_to_proper_check():
                    logging.info('%s does proper check of %s', self.identification, self._container.identification)
                    self.statistics.report_agent_physically_inspected(self.identification)
                    self._state = AgentState.INSPECTION
                else:
                    logging.info('%s does quick check of %s', self.identification, self._container.identification)
                    self.statistics.report_agent_virtually_inspected(self.identification)
                    logging.info('%s clears %s', self.identification, self._container.identification)
                    self._container.cleared_by_customs = ContainerState.CLEARED
                    self.statistics.report_country_correct(self._container.declaration.source)
                    self.statistics.report_company_correct(self._container.company)
                    if (set(self._container.declaration.items) == set(self._container.items)) and (self._container.declaration.declared_tax == self._container.tax):
                        self.statistics.container_cleared_correctly()
                    else:
                        self.statistics.container_cleared_incorrectly()
                    self._state = AgentState.IDLE
        elif self._state == AgentState.A_WAITING_PA:
            logging.info('%s waits for PA', self.identification)
        elif self._state == AgentState.INSPECTION:
            # logging.debug('%s at position %d,%d and target is %d,%d', self.identification, self.pos_x, self.pos_y, self._target_position[0], self._target_position[1])
            if self._target_position != self.position:
                logging.info('%s moving to %s', self.identification, self._container.identification)
                path = LineString([self.position, self._target_position])
                pos = path.interpolate(CustomsAgent.SPEED)
                self.pos_x = pos.x
                self.pos_y = pos.y
            else:
                logging.info('%s inspecting %s', self.identification, self._container.identification)
                if self._in_current_state < CustomsAgent.INSPECTION_DUR:
                    self._in_current_state += 1
                else:
                    self._in_current_state = 0
                    if self.inspect_container():
                        if self.inspect_tax():
                            logging.info('%s cleared %s', self.identification, self._container.identification)
                            self._container.cleared_by_customs = ContainerState.CLEARED
                            self.statistics.report_country_correct(self._container.declaration.source)
                            self.statistics.report_company_correct(self._container.company)
                            self.statistics.container_cleared_correctly()
                            self.statistics.put_company_last_tax(self._container.company, self._container.tax)
                        else:
                            logging.info('%s rejects %s because of incorrect declared tax', self.identification, self._container.identification)
                            self._container.cleared_by_customs = ContainerState.UNCLEARED
                            self.statistics.report_country_error(self._container.declaration.source)
                            self.statistics.report_company_error(self._container.company)
                            self.statistics.container_rejected()
                    else:
                        logging.info('%s rejects %s because of incorrect declaration', self.identification, self._container.identification)
                        self._container.cleared_by_customs = ContainerState.UNCLEARED
                        self.statistics.report_country_error(self._container.declaration.source)
                        self.statistics.report_company_error(self._container.company)
                        self.statistics.container_rejected()
                    self._state = AgentState.RETURNING
                    self._container = None
        elif self._state == AgentState.RETURNING:
            if self.position != self._home_position:
                logging.info('%s moving home', self.identification)
                path = LineString([self.position, self._home_position])
                pos = path.interpolate(CustomsAgent.SPEED)
                self.pos_x = pos.x
                self.pos_y = pos.y
            else:
                logging.info('%s is home', self.identification)
                self._state = AgentState.IDLE
        else:
            logging.info('%s in unknown state', self.identification)
            pass


class PortAuthorityOfficer(Agent):
    CHECK_DUR = 2
    INSPECTION_DUR = 2
    SPEED = 50

    def __init__(self,  identification: str, home_position: (int, int), cust_computer_position: (int, int), statistics):
        super().__init__(identification, home_position, statistics)
        self._container_position = None
        self._agent = None
        self._cust_computer_position = cust_computer_position

    def decide_to_proper_check(self):
        dangerous = "NonDangerous"
        if self._container.declaration.has_dangerous():
            dangerous = "Dangerous"
            # return False
        if execute_analysis("Dangerous", "con", dangerous): #self._container.declaration.has_dangerous():
            # for dangerous items, proper check is mandatory
            return True
        # otherwise, throw a die
        return not getrandbits(1)

    def decide_phys_inspection(self):
        return not getrandbits(1)

    @property
    def assigned_agent(self) -> CustomsAgent:
        return self._agent

    @assigned_agent.setter
    def assigned_agent(self, agent: CustomsAgent):
        self._agent = agent
        agent.wait_for_pa()
        self._state = AgentState.PA_MOVING_TO_A
        self._target_position = agent.home_position

    def assign_container(self, container: Container, container_position: (int, int)):
        self._container = container
        self._state = AgentState.CHECK
        self._in_current_state = 0
        self._container_position = container_position

    def reset_container(self):
        self._container = None
        self._container_position = None

    def set_target_position(self, position: (int, int)):
        self._target_position = position

    def step(self):
        if self._state == AgentState.IDLE:
            logging.info('%s does nothing', self.identification)
            pass
        elif self._state == AgentState.CHECK:
            self._in_current_state += 1
            logging.info('%s evaluates %s', self.identification, self._container.identification)
            if self._in_current_state == PortAuthorityOfficer.CHECK_DUR:
                self._in_current_state = 0
                if self.decide_to_proper_check():
                    logging.info('%s decided to proper check %s', self.identification, self._container.identification)
                    self._state = AgentState.PA_DETAILED_CHECK
                else:
                    logging.info('%s does quick check of %s', self.identification, self._container.identification)
                    self.statistics.report_pa_virtually_inspected(self.identification)
                    logging.info('%s clears %s', self.identification, self._container.identification)
                    self._container.cleared_by_pa = ContainerState.CLEARED
                    self._state = AgentState.IDLE
        elif self._state == AgentState.PA_DETAILED_CHECK:
            if self.position != self._cust_computer_position:
                # need to move to the customs computer
                logging.info('%s moving to the customs computer', self.identification)
                path = LineString([self.position, self._cust_computer_position])
                pos = path.interpolate(PortAuthorityOfficer.SPEED)
                self.pos_x = pos.x
                self.pos_y = pos.y
            else:
                # at the customs computer
                self._in_current_state += 1
                logging.info('%s reading full declaration of %s', self.identification, self._container.identification)
                if self._in_current_state == PortAuthorityOfficer.CHECK_DUR:
                    self._in_current_state = 0
                    if self.decide_phys_inspection():  # whether to go for inspection
                        logging.info('%s decided for inspection of %s and asks for the cust agent', self.identification, self._container.identification)
                        self.statistics.report_pa_physically_inspected(self.identification)
                        self._state = AgentState.PA_REQUEST_A
                    else:  # no inspection decided, thus clear the container and go home
                        logging.info('%s clears %s from the customs office', self.identification, self._container.identification)
                        self.statistics.report_pa_computer_inspected(self.identification)
                        self._container.cleared_by_pa = ContainerState.CLEARED
                        self.reset_container()
                        self._state = AgentState.RETURNING
        elif self._state == AgentState.PA_REQUEST_A:
            logging.info('%s waits for customs agent assignment', self.identification)
        elif self._state == AgentState.PA_MOVING_TO_A:
            if self._target_position != self.position:
                logging.info('%s moving to %s', self.identification, self._agent.identification)
                path = LineString([self.position, self._target_position])
                pos = path.interpolate(PortAuthorityOfficer.SPEED)
                self.pos_x = pos.x
                self.pos_y = pos.y
            else:
                self._state = AgentState.PA_CHECK_WITH_A
        elif self._state == AgentState.PA_CHECK_WITH_A:
            self._state = AgentState.INSPECTION
            self._target_position = self._container_position
            self._agent.ask_inspection(self._container)
            self._agent.set_container_position(self._container_position)
        elif self._state == AgentState.INSPECTION:
            if self._target_position != self.position:  # moving to container
                logging.info('%s moving to %s', self.identification, self._container.identification)
                path = LineString([self.position, self._target_position])
                pos = path.interpolate(PortAuthorityOfficer.SPEED)
                self.pos_x = pos.x
                self.pos_y = pos.y
            else:   # already at the container
                # actual inspection is done by the customs agent
                if self._container.cleared_by_customs != ContainerState.DELIVERED:
                    logging.info('%s inspects the container with %s', self.identification, self._agent.identification)
                    # the status of the container is "copied" form the customs agent
                    # actual check is done by the customs agent
                    self._container.cleared_by_pa = self._container.cleared_by_customs
                    self._state = AgentState.RETURNING
                    self.reset_container()
                else:  # do nothing and wait for customs agent
                    logging.info('%s waits at container for %s', self.identification, self._agent.identification)
        elif self._state == AgentState.RETURNING:
            if self.position != self._home_position:
                logging.info('%s moving home', self.identification)
                path = LineString([self.position, self._home_position])
                pos = path.interpolate(PortAuthorityOfficer.SPEED)
                self.pos_x = pos.x
                self.pos_y = pos.y
            else:
                logging.info('%s is home', self.identification)
                self._state = AgentState.IDLE
        else:
            logging.info('%s in unknown state', self.identification)
            pass


class LeadCustomsAgent(Agent):
    INSPECTION_DURATION = 100
    INSPECTION_COOLDOWN = 500  # how many steps after inspection is an agent ignored

    def __init__(self,  identification: str, home_position: (int, int), statistics):
        super().__init__(identification, home_position, statistics)
        self.__agents_under_inspection = {}
        self.__agents_after_inspection = {}

    def inspect_lazy_agent(self, agent: CustomsAgent) -> None:
        if agent not in self.__agents_under_inspection.keys():
            logging.info(f'{self.identification} starts inspecting {agent.identification}')
            self.__agents_under_inspection[agent] = 1

    def agents_under_inspection(self) -> list[CustomsAgent]:
        return list(self.__agents_under_inspection.keys())

    def agents_inspected(self) -> list[CustomsAgent]:
        return list(self.__agents_under_inspection.keys()) + list(self.__agents_after_inspection.keys())

    def step(self):
        for agent in list(self.__agents_under_inspection.keys()):
            self.__agents_under_inspection[agent] += 1
            if self.__agents_under_inspection[agent] > LeadCustomsAgent.INSPECTION_DURATION:
                agent.punish()
                logging.info(f'{self.identification} punishes {agent.identification}')
                self.__agents_under_inspection.pop(agent)
                self.__agents_after_inspection[agent] = 1
        for agent in list(self.__agents_after_inspection.keys()):
            self.__agents_after_inspection[agent] += 1
            if self.__agents_after_inspection[agent] > LeadCustomsAgent.INSPECTION_COOLDOWN:
                self.__agents_after_inspection.pop(agent)

