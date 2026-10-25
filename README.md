# CS-350 Emerging Systems Architectures and Technologies

## Overview

This repository contains selected artifacts completed in CS-350 Emerging Systems Architectures and Technologies at Southern New Hampshire University. The thermostat project demonstrates my ability to write software that interfaces with hardware, work with sensors and GPIO components, and design an embedded system that responds to user input and temperature readings.

## Included Artifacts

### Thermostat Project

**Files included:**

- Embedded_Thermostat_System/Thermostat.py
- Embedded_Thermostat_System/CS350 Final Project Thermostat Diagram - Justin Carlo Florida.pdf

The thermostat project uses a Raspberry Pi, temperature sensor, LCD, buttons, and LEDs to demonstrate how hardware and software work together in an embedded system. The program reads temperature data, displays information, and responds to user input to control the thermostat behavior. The state-machine diagram shows the system’s states and how it responds to inputs.

## Reflection

### Summarize the project and what problem it was solving.

The project was to design and program a thermostat using a Raspberry Pi and connected components. It demonstrates how an embedded system can read temperature data, display system information, and respond to button input. The project brought together hardware connections, GPIO configuration, sensor readings, and control logic.

### What did you do particularly well?

I did well at integrating the hardware and software and testing the components as I built the system. When a button did not control the expected LED, I checked the physical wiring and corrected the button-to-GPIO assignments in the code to match the actual connections. I also used the state-machine diagram to organize and explain the system’s behavior.

### Where could you improve?

I could improve by planning and verifying the GPIO assignments earlier and documenting the wiring and code relationships more clearly as I build. I would also add more structured tests for individual inputs and system states so issues can be identified sooner.

### What tools and/or resources are you adding to your support network?

I used the Raspberry Pi, Python, GPIO libraries, the course lab instructions, and the provided hardware examples. I also used draw.io to create the state-machine diagram. In future projects, I can continue using official hardware and software documentation, testing tools, and developer communities to research unfamiliar components and troubleshoot problems.

### What skills from this project will be particularly transferable to other projects and/or course work?

The most transferable skills are troubleshooting, testing hardware and software together, reading technical instructions, and breaking a complex problem into smaller steps. Understanding GPIO, sensors, user input, and state-based control will also help with future embedded systems and software projects.

### How did you make this project maintainable, readable, and adaptable?

I used clear variable names and organized the program around the thermostat’s inputs, outputs, and control behavior. The state-machine diagram makes the system’s behavior easier to understand. Testing components individually also made it easier to find and correct problems. These practices make future changes, such as adjusting GPIO assignments or adding system behavior, easier to manage.

## Author

**Justin Carlo Florida**  
Computer Science Student | Software Engineering
