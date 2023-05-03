Requirements
------------

- Python 3.10+
- Java 11+
  - only for the dataflow analysis
- additional python modules
  - shapely
  - dataclass-wizard


Setup for dataflow analysis execution
-------------------------------------

- Download the PCM models from https://github.com/FluidTrust/CaseStudies/tree/main/bundles/fluidTrustCaseStudy-Simplified
  - ```
    cd FluidTrustDemo
    git clone https://github.com/FluidTrust/CaseStudies.git
    ```
- Download the dataflow analysis from https://updatesite.palladio-simulator.com/fluidtrust/casestudies/nightly/
- Extract the downloaded dataflow analysis to the folder `analysis`
- Add `--launcher.suppressErrors` to the `analysis/eclipse.ini` file
  - otherwise, a box with execution results appears after each call


Configuration
-------------

- stored in the `config.yaml` file
- to skip dataflow analysis execution, set `analysis->fake` to `True`

Execution
---------

Execute the [simulation.py](simulation.py) file.
Terminate the program by closing the window or pressing `F10`.

Components in the system
------------------------

**Item**

- an item in the container
- passive
- a list of items taken from the [Amazon dataset](amazondata_electronics.txt)
  - dangerous items are of the kind `GPS_OR_NAVIGATION_SYSTEM` and `SURVEILANCE_SYSTEMS`

**Container**

- passive
- items to the container are randomly selected from the list
- items in the container do not repeat
- a container has a `Declaration`
  - it contains a list of items
  - with a probability, the list in the declaration does not correspond with the list in the `Container`
    - now there is a hardcoded probability
  - it has a *source* and *destination*
    - they are taken from the [list of all countries](locations.txt)
      - the file is a CSV file with three columns
      - 1st column - the name of a country
      - 2nd column - probability the customs agent will inspect containers from the country (not yet used)
      - 3rd column - probability the PA officer will inspect containers from the country (not yet used)
- container needs to be cleared by both customs and port authority

**LeadCustomsAgent**

- does nothing for now

**CustomsAgent**

- active
- states of the behavior
  - IDLE - does nothing
  - CHECKING 
    - has assigned a container
    - decides for physical inspection
      - if source country error-rate is too high (or unknown) -> phys-inspection
      - if transport company error-rate is too high (or unknown) -> phys-inspection
      - if the reported tax is significantly different from the last one -> phys-inspection
      - in the rest of cases randomly decides for physical inspection
  - INSPECTION
    - moves to the container
    - once at the container, inspects it (i.e., compares the list of items in the declaration and in the container) and then based on the comparison either clears or refuses to clear it
  - RETURNING to the office after inspection
  - WAITING FOR PA OFFICE
    - a PA officer asks for physical inspection, the customs agent waits for the PA officer to come to the office
    - then, the customs agent switches to the INSPECTION state

**PA officer**

- active
- states of the behavior
  - IDLE - does nothing
  - CHECKING
    - has assigned container
    - decide for detailed checking, which has to be performed from a customs computer
      - mandatory for dangerous items
      - randomly decide for other
  - DETAILED_CHECKING
    - moves to the customs computer
    - randomly (for now, should use probabilities from the location list) decides for detailed inspection and asks for a customs agent assistance
  - REQUEST_ASSISTANCE
    - waits for assigning a customs agent
    - if an agent is assigned, switches to MOVING_TO_AGENT
  - MOVING_TO_AGENT
    - moves to the assigned agent office
    - if in the office, both switches to INSPECTION
  - INSPECTION
    - moves to the container
    - together with the customs agent, they inspect the container
      - the actual inspection is done by the customs agent only, the PA officer takes the result
  - RETURNING
    - returning to the own office after detailed checking or inspection

Whole simulation
----------------

- steps
  - containers arrive with regular interval and are assigned to an empty slot
    - there is a limited number of slots for containers
      - if all of them are occupied, then new containers are not generated
  - containers need to be cleared by both PA and customs
    - once cleared (or uncleared), the container is removed
  - if there is an unclearead container by PA (and unassigned), the container is assigned to an available agent
  - if there is a cleared container by PA but uncleared by customs (and unassigned to an agent), the container is assigned to an available agent
  - if a PA officer waits for a customs agent, an available one is assigned
  - customs agents and PA officers perform their step

Implemented scenarios (slides from Maximillian)
-----------------------------------------------

- S1 Error Rate with Countries
  - done
- S2 Import from Luxury or Restricted Items
  - NO as it is quite similar to S3
- S3 Import from Dangerous Items
  - done
  - a container with declared dangerous items requires detailed check from PA
- S4 New Company
  - done
- S5 Expert Access
  - NO as it is similar to S6
- S6 Exchange Data with Foreign Agency
  - done but slightly modified
  - PA officer needs to use a Customs computer for detailed inspection (i.e., data is shared)
  - PA officer cannot physically check a container and has to be accompanied by a custom agent
- S7 Import Taxes
  - done

Dynamic rules (like Ensembles)
------------------------------

- Rules are evaluated in each step of the simulation
- Currently, a single rule only
  - `CustomsAgentTooLazyRule` detects a lazy agent, i.e., an agent that "inspects" containers virtually to much
    - if the agent is detected, it is inspected by the Lead agent and eventually the Lead agent punishes the lazy agent
      - `LazyCustomsAgent` simulates a lazy agent
