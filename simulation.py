#!/usr/bin/env python3
import utils
from components import Container, CustomsAgent, AgentState, ContainerState, LeadCustomsAgent, PortAuthorityOfficer
from rules import CustomsAgentTooLazyRule
from special import LazyCustomsAgent
from helpers import generate_container, Statistics
from utils import setup_logging

from tkinter import *
from PIL import Image, ImageTk
import logging


CONTAINER_SLOTS_POSITIONS = [
    (50, 10),
    (50, 100),
    (50, 190),
    (50, 280),
    (50, 370),
    (50, 460),
    (50, 550)
]

STATISTICS = Statistics()


class ContainerSlot:
    def __init__(self, position: (int, int)):
        self._position = position
        self.container = None
        self._agent = None

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, cont: Container):
        self._container = cont

    def remove_container(self):
        self.container = None
        self.agent = None

    @property
    def position(self):
        return self._position

    @property
    def inspection_point(self):
        return self._position[0] + 110, self._position[1]

    @property
    def agent(self):
        return self._agent

    @agent.setter
    def agent(self, agent):
        self._agent = agent


class Slots:
    def __init__(self):
        self.slots = []
        self.removed_containers = []
        for i in range(len(CONTAINER_SLOTS_POSITIONS)):
            self.slots.append(ContainerSlot(CONTAINER_SLOTS_POSITIONS[i]))

    def slot(self, i):
        return self.slots[i]

    def __getitem__(self, index):
        if index < len(self.slots):
            return self.slots[index]
        else:
            raise IndexError('slot ouf of bounds')

    def number_of_slots(self):
        return len(self.slots)

    def get_empty(self):
        for slot in self.slots:
            if slot.container is None:
                return slot
        return None

    def slot_with_unassigned_container(self):
        for slot in self.slots:
            if (slot.container is not None) and (slot.agent is None):
                return slot
        return None

    def remove_container(self, container):
        for slot in self.slots:
            if container is slot.container:
                slot.remove_container()
                self.removed_containers.append(container)
                break


class Simulation:
    SMALLEST_PERIOD_FOR_CONTAINER = 10

    def __init__(self):
        self.slots = Slots()
        agent_classes = []
        num_of_lazy = utils.CONFIG.simulation.lazy_agents
        for i in range(3):
            if num_of_lazy:
                agent_classes.append(LazyCustomsAgent)
                num_of_lazy -= 1
            else:
                agent_classes.append(CustomsAgent)
        self.agents = [
             agent_classes[0]('Agent01', (700, 100), STATISTICS),
             agent_classes[1]('Agent02', (700, 270), STATISTICS),
             agent_classes[2]('Agent03', (700, 440), STATISTICS)
        ]
        self.lead_agent = LeadCustomsAgent('LeadAgent01', (975, 270), STATISTICS)
        self.cust_computer_for_pa = (975, 440)
        self.paagents = [
            PortAuthorityOfficer('PortAuthorityAgent01', (340, 735), self.cust_computer_for_pa, STATISTICS),
            PortAuthorityOfficer('PortAuthorityAgent02', (580, 735), self.cust_computer_for_pa, STATISTICS),
            PortAuthorityOfficer('PortAuthorityAgent03', (820, 735), self.cust_computer_for_pa, STATISTICS)
        ]
        self.containers = []
        self.steps_from_last_container = Simulation.SMALLEST_PERIOD_FOR_CONTAINER
        self.rules = [CustomsAgentTooLazyRule(self.lead_agent, STATISTICS, self.agents)]

    def available_agent(self):
        for agent in self.agents:
            if agent.state == AgentState.IDLE:
                return agent
        return None

    def available_pa(self):
        for agent in self.paagents:
            if agent.state == AgentState.IDLE:
                return agent
        return None

    def step(self):
        for rule in self.rules:
            rule.evaluate()

        if self.steps_from_last_container != Simulation.SMALLEST_PERIOD_FOR_CONTAINER:
            self.steps_from_last_container += 1
        else:  # generate new container
            slot = self.slots.get_empty()
            if slot is not None:
                container = generate_container()
                logging.info("%s arrived", container.identification)
                slot.container = container
                self.steps_from_last_container = 0
            else:
                logging.info('No empty slot')

        for slot in self.slots:
            if slot.container is not None and slot.container.state != ContainerState.DELIVERED:
                self.slots.remove_container(slot.container)
            elif slot.container is not None and slot.container.cleared_by_pa != ContainerState.DELIVERED and slot.container.cleared_by_customs != ContainerState.DELIVERED:
                slot.container.state = slot.container.cleared_by_pa
            elif slot.container is not None and slot.container.cleared_by_pa == ContainerState.CLEARED and slot.container.cleared_by_customs == ContainerState.DELIVERED and isinstance(slot.agent, PortAuthorityOfficer):
                slot.agent = None

        while True:
            slot = self.slots.slot_with_unassigned_container()
            if slot:
                if slot.container.cleared_by_pa == ContainerState.DELIVERED:  # container not yet cleared by PA
                    agent = self.available_pa()
                    if agent:
                        #ipoint = slot.inspection_point
                        #ipoint = (ipoint[0] + 30, ipoint[1])
                        agent.assign_container(slot.container, slot.inspection_point)
                        logging.info('Assigning %s to %s', agent.identification, slot.container.identification)
                        slot.agent = agent
                    else:
                        logging.info('No PA agent available')
                        break
                elif slot.container.cleared_by_pa == ContainerState.CLEARED and slot.container.cleared_by_customs ==ContainerState.DELIVERED:  # cleared by PA but not by customs
                    agent = self.available_agent()
                    if agent:
                        slot.agent = agent
                        agent.assign_container(slot.container)
                        agent.set_container_position(slot.inspection_point)
                        logging.info('Assigning %s to %s', agent.identification, slot.container.identification)
                    else:
                        logging.info('No customs agent available')
                        break
            else:
                logging.info('No unassigned container')
                break

        for agent in self.paagents:
            if agent.state == AgentState.PA_REQUEST_A:
                cust_agent = self.available_agent()
                if cust_agent:
                    logging.info('assigning %s to %s', cust_agent.identification, agent.identification)
                    agent.assigned_agent = cust_agent
                    STATISTICS.report_pa_paired_with_agent(agent.identification, cust_agent.identification)
                else:
                    logging.info('%s waits for the customs agent but no one is available', agent.identification)

        for agent in self.paagents:
            agent.step()

        for agent in self.agents:
            agent.step()

        self.lead_agent.step()


root = Tk()
root.title('FluidTrust demo')
root.tk.call('wm', 'iconphoto', root._w, PhotoImage(file='images/icon.png'))


def terminate_app():
    logging.info('Terminating')
    print(STATISTICS.print_statistics())
    root.destroy()


class App(Canvas):

    STEP = 100
    WIDTH = 1200
    HEIGHT = 857

    def __init__(self, parent):
        super().__init__(parent, width=App.WIDTH, height=App.HEIGHT)
        self.pack()
        bgim = Image.open('images/back.png')
        self.agent_im = Image.open('images/back.png')
        self.bgimtk = ImageTk.PhotoImage(bgim)
        self.create_image(0, 0, image=self.bgimtk, anchor=NW, tags="bg")

        self.simulation = Simulation()
        agentim = Image.open('images/agent.png')
        leadagentim = Image.open('images/leadagent.png')
        authagentim = Image.open('images/authagent.png')
        inspim = Image.open('images/magnify.png')
        self.agentimtk = ImageTk.PhotoImage(agentim)
        self.leadagentimtk = ImageTk.PhotoImage(leadagentim)
        self.authagentimtk = ImageTk.PhotoImage(authagentim)
        self.inspimtk = ImageTk.PhotoImage(inspim)
        for agent in self.simulation.agents:
            self.create_image(agent.pos_x, agent.pos_y, image=self.agentimtk, anchor=NW, tags=agent.identification)
        self.create_image(self.simulation.lead_agent.pos_x, self.simulation.lead_agent.pos_y, image=self.leadagentimtk, anchor=NW, tags=self.simulation.lead_agent.identification)
        for agent in self.simulation.paagents:
            self.create_image(agent.pos_x, agent.pos_y, image=self.authagentimtk, anchor=NW, tags=agent.identification)
        contim = Image.open('images/container01.png')
        self.contimtk = ImageTk.PhotoImage(contim)
        dcontim = Image.open('images/dcontainer01.png')
        self.dcontimtk = ImageTk.PhotoImage(dcontim)
        self.after(App.STEP, self.on_timer)
        self._terminate = False
        self.bind("<F10>", self.terminate_simulation)
        self.focus_set()

    def update_containers(self):
        for slot in self.simulation.slots:
            container = slot.container
            if container is not None:
                if not self.find_withtag(container.identification):
                    if container.dangerous:
                        self.create_image(slot.position[0], slot.position[1], image=self.dcontimtk, anchor=NW, tags=container.identification)
                    else:
                        self.create_image(slot.position[0], slot.position[1], image=self.contimtk, anchor=NW, tags=container.identification)
                    self.create_text(slot.position[0] + 32, slot.position[1], anchor=NW, text='CUST  ?', tags=container.identification+'_C', font=('Monospace 15 bold'))
                    self.create_text(slot.position[0] + 32, slot.position[1] + 15, anchor=NW, text='PA    ?', tags=container.identification + '_PA', font=('Monospace 15 bold'))
                    if set(container.declaration.items) != set(container.items):  # faked declaration
                        self.create_text(slot.position[0] + 10, slot.position[1] + 30, anchor=NW, text='FAKED', tags=container.identification + '_FAKED', font=('Monospace 20 bold'), fill='orange')
                    elif container.tax != container.declaration.declared_tax:
                        self.create_text(slot.position[0] + 10, slot.position[1] + 30, anchor=NW, text='FAKED TAX', tags=container.identification + '_FAKED', font=('Monospace 20 bold'), fill='orange')
                else:
                    pa_text = self.find_withtag(container.identification + '_PA')
                    if slot.container.cleared_by_pa == ContainerState.CLEARED:
                        self.itemconfigure(pa_text[0], text='PA   OK', fill='green')
                    elif slot.container.cleared_by_pa == ContainerState.UNCLEARED:
                        self.itemconfigure(pa_text[0], text='PA    x', fill='red')
                    cust_text = self.find_withtag(container.identification + '_C')
                    if slot.container.cleared_by_customs == ContainerState.CLEARED:
                        self.itemconfigure(cust_text[0], text='CUST OK', fill='green')
                    elif slot.container.cleared_by_customs == ContainerState.UNCLEARED:
                        self.itemconfigure(cust_text[0], text='CUST  x', fill='red')

        for container in self.simulation.slots.removed_containers:
            self.delete(container.identification)
            self.delete(container.identification + '_PA')
            self.delete(container.identification + '_C')
            self.delete(container.identification + '_FAKED')
        self.simulation.slots.removed_containers.clear()

    def update_agents(self):
        under_inspection = self.simulation.lead_agent.agents_under_inspection()
        for agent in self.simulation.agents:
            agent_im = self.find_withtag(agent.identification)
            self.coords(agent_im[0], agent.pos_x, agent.pos_y)
            if agent in under_inspection:
                text = self.find_withtag(agent.identification + '_INSP_TEXT')
                im = self.find_withtag(agent.identification + '_INSP_IM')
                if not text:
                    self.create_text(agent.pos_x, agent.pos_y + 60, anchor=NW, text='UNDER INSPECTION', tags=agent.identification + '_INSP_TEXT', font=('Monospace 15 bold'), fill='red')
                    self.create_image(agent.pos_x + 10, agent.pos_y + 10, image=self.inspimtk, anchor=NW, tags=agent.identification + '_INSP_IM')
                else:
                    self.coords(text[0], agent.pos_x, agent.pos_y + 60)
                    self.coords(im[0], agent.pos_x + 10, agent.pos_y + 10)
            else:
                text = self.find_withtag(agent.identification + '_INSP_TEXT')
                im = self.find_withtag(agent.identification + '_INSP_IM')
                if text:
                    self.delete(text[0])
                    self.delete(im[0])

    def update_paagents(self):
        for agent in self.simulation.paagents:
            agent_im = self.find_withtag(agent.identification)
            self.coords(agent_im[0], agent.pos_x, agent.pos_y)

    def on_timer(self):
        if not self._terminate:
            logging.info('Tick')
            self.simulation.step()
            self.update_agents()
            self.update_paagents()
            self.update_containers()
            self.after(App.STEP, self.on_timer)
        else:
            terminate_app()

    def terminate_simulation(self, event):
        self.create_text(App.WIDTH//2, App.HEIGHT//2, anchor=CENTER, text='Terminating....')
        self._terminate = True



#  MAIN
setup_logging()

app = App(root)
root.resizable(width=False, height=False)
root.protocol("WM_DELETE_WINDOW", terminate_app)
root.mainloop()
