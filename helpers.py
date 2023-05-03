#!/usr/bin/env python3

from components import Item, ListOfItems, Container, Declaration
import re
from random import getrandbits, randrange
from dataclasses import dataclass
from collections import defaultdict, Counter

#https://github.com/sameeravithana/Amazon-E-commerce-Data-set

NUMBER_OF_ITEMS_IN_THE_CONTAINER = 10
CURRENT_CONTAINER = 0
TAX = 15  # in percents

#ITEM_RE  = re.compile('ITEM ([0-9]+)')
TITLE_RE = re.compile('Title=(.+)')
PRODUCTTYPE_RE = re.compile('ProductTypeName=(.*)')
PRICE_RE = re.compile('ListPrice=([0-9]*)USD.*')

DANGEROUS_TYPES = ['GPS_OR_NAVIGATION_SYSTEM', 'SURVEILANCE_SYSTEMS']


def read_items() -> list:
    items = []
    with open('amazondata_electronics.txt') as f:
        title = None
        kind = None
        price = 0
        for line in f:
            line = line.strip()
            if len(line) == 0:
                if title and kind and price:
                    is_dangerous = True if kind in DANGEROUS_TYPES else False
                    items.append(Item(kind, 1, is_dangerous, title, price))
                    title = None
                    kind = None
                    price = 0
                    continue
            result = TITLE_RE.match(line)
            if result:
                title = result.group(1)
                continue
            result = PRODUCTTYPE_RE.match(line)
            if result:
                kind = result.group(1)
            result = PRICE_RE.match(line)
            if result:
                price = int(result.group(1))
    return items


def read_shipping_companies() -> list:
    companies = []
    with open('shipping.txt') as f:
        for line in f:
            line = line.strip()
            companies.append(line)
    return companies


@dataclass(frozen=True)
class Location:
    name: str
    dangerous_prob: int
    fake_prob: int

    @classmethod
    def from_line(cls, line: str):
        sp = line.split('\t')
        return cls(sp[0], int(sp[1]), int(sp[2]))


def read_locations() -> list:
    locations = []
    with open('locations.txt') as f:
        for line in f:
            line = line.strip()
            locations.append(Location.from_line(line))
    return locations


ITEMS = read_items()
LOCATIONS = read_locations()
COMPANIES = read_shipping_companies()


class Statistics:
    def __init__(self):
        self.country_stat = defaultdict(Counter)
        self.company_stat = defaultdict(Counter)
        self.containers_stat = Counter()
        self.last_tax = defaultdict(lambda: 1)  # TODO workaround
        self.agent_stat = defaultdict(Counter)
        self.pa_officer_stat = defaultdict(Counter)
        self.pairing_stat = defaultdict(Counter)

    def report_country_error(self, country: str):
        self.country_stat[country].update(error=1)

    def report_country_correct(self, country: str):
        self.country_stat[country].update(ok=1)

    def country_error_rate(self, country: str) -> float:
        s = self.country_stat[country]["error"] + self.country_stat[country]["ok"]
        if not s:
            return 1.  # no info yet, thus returning max value
        return self.country_stat[country]["error"] / s

    def report_company_error(self, country: str):
        self.company_stat[country].update(error=1)

    def report_company_correct(self, country: str):
        self.company_stat[country].update(ok=1)

    def company_error_rate(self, country: str) -> float:
        s = self.company_stat[country]["error"] + self.company_stat[country]["ok"]
        if not s:
            return 1.  # no info yet, thus returning max value
        return self.company_stat[country]["error"] / s

    def container_cleared_correctly(self):
        self.containers_stat.update(cleared_ok=1)

    def container_cleared_incorrectly(self):
        self.containers_stat.update(cleared_bad=1)

    def container_rejected(self):
        self.containers_stat.update(rejected=1)

    def company_last_tax(self, company) -> int:
        return self.last_tax[company]

    def put_company_last_tax(self, company, tax):
        self.last_tax[company] = tax

    def report_agent_physically_inspected(self, agent):
        self.agent_stat[agent].update(physical=1)

    def report_agent_virtually_inspected(self, agent):
        self.agent_stat[agent].update(virtual=1)

    def agent_physically_inspected(self, agent) -> int:
        return self.agent_stat[agent]['physical']

    def agent_virtually_inspected(self, agent) -> int:
        return self.agent_stat[agent]['virtual']

    def report_pa_physically_inspected(self, officer):
        self.pa_officer_stat[officer].update(physical=1)

    def report_pa_computer_inspected(self, officer):
        self.pa_officer_stat[officer].update(computer=1)

    def report_pa_virtually_inspected(self, officer):
        self.pa_officer_stat[officer].update(virtual=1)

    def report_pa_paired_with_agent(self, officer, agent):
        self.pairing_stat[officer].update({agent: 1})

    def print_statistics(self):
        print('Statistics')
        print('==========')
        print('Containers')
        print('----------')
        print(f'Cleared: {self.containers_stat["cleared_ok"] + self.containers_stat["cleared_bad"]}, out of it incorrectly {self.containers_stat["cleared_bad"]}, Rejected: {self.containers_stat["rejected"]}')
        print('Countries error rate')
        print('--------------------')
        for country in self.country_stat.keys():
            print(f'{country}: {self.country_error_rate(country)}')
        print('Companies error rate')
        print('--------------------')
        for company in self.company_stat.keys():
            print(f'{company}: {self.company_error_rate(company)}')
        print('Customs agents')
        print('--------------')
        for agent in sorted(self.agent_stat.keys()):
            print(f'{agent} inspected: physically {self.agent_stat[agent]["physical"]}, virtually {self.agent_stat[agent]["virtual"]}')
        print('PA officers')
        print('-----------')
        for officer in sorted(self.pa_officer_stat.keys()):
            print(f'{officer} inspected: physically {self.pa_officer_stat[officer]["physical"]}, from customs computer {self.pa_officer_stat[officer]["computer"]}, virtually {self.pa_officer_stat[officer]["virtual"]}')
        print('Pairing')
        print('-------')
        for officer in sorted(self.pairing_stat.keys()):
            print(f'{officer} paired with: ', end='')
            for agent in sorted(self.pairing_stat[officer]):
                print(f'{agent} {self.pairing_stat[officer][agent]} times ', end='')
            print()
        print('END-OF-STATISTICS')


def get_random_list_of_items(size: int) -> ListOfItems:
    length = len(ITEMS)
    item_ids = []
    while len(item_ids) != size:
        i = randrange(0, length)  # get random item
        if i not in item_ids:     # do not repeat items in the list
            item_ids.append(i)
    items = []
    for i in item_ids:
        items.append(ITEMS[i])
    return items


def get_items_tax(lst: ListOfItems) -> int:
    s = 0
    for item in lst:
        s += item.price
    tax = int(s * TAX / 100)
    return tax if tax else 1


def get_list_for_declaration_and_tax(lst: ListOfItems) -> (ListOfItems, int):
    """With small probability return another list and maybe also a wrong tax"""
    modify = not getrandbits(2)
    if modify:
        newlist = get_random_list_of_items(len(lst))
        return newlist, get_items_tax(newlist)
    else:
        if not getrandbits(2):
            return lst, 3
        else:
            return lst, get_items_tax(lst)


def pretend_not_dangerous(lst: ListOfItems) -> ListOfItems:
    updated_list = []
    for item in lst:
        if item.is_dangerous:
            item = Item(item.kind, item.amount, False, item.description)
        updated_list.append(item)
    return updated_list


def get_random_source_and_destination() -> tuple:
    length = len(LOCATIONS)
    return LOCATIONS[randrange(0, length)], LOCATIONS[randrange(0, length)]


def get_random_company() -> str:
    return COMPANIES[randrange(0, len(COMPANIES))]


def generate_container() -> Container:
    actual_items = get_random_list_of_items(NUMBER_OF_ITEMS_IN_THE_CONTAINER)
    source, destination = get_random_source_and_destination()
    declared_items, tax = get_list_for_declaration_and_tax(actual_items)
    actual_tax = get_items_tax(actual_items)
    global CURRENT_CONTAINER
    CURRENT_CONTAINER += 1
    return Container(f'Container{CURRENT_CONTAINER:03}', get_random_company(), actual_items, actual_tax, Declaration(declared_items, source.name, destination.name, tax))
