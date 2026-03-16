# Smart Light

- Template: home automation
- Purpose: Home automation
- Skill level: beginner
- Budget mode: mid
- Status: in progress
- Tags: lighting, wifi

## Inputs
- Components: Arduino, LED strip, relay module
- Requirements: Wifi controlled, mobile app
- Constraints: Indoor only

## Narrative Plan
# Smart Light

Template: home automation
Purpose: Home automation
Skill level: beginner
Budget mode: mid

## Summary
Build a system around Arduino, LED strip, relay module and satisfy: Wifi controlled, mobile app.

## Build Steps
- Review the home automation requirements and confirm the goal: Home automation.
- Lay out the controller, power path, and peripherals before wiring anything.
- Wire one component at a time and test each connection before adding the next part.
- Load a minimal firmware sketch or script to verify communication with each module.
- Integrate the full workflow and test against the main success criteria.

## Safety
- Validate current draw before powering motors, relays, or heating elements.
- Do not connect 5V outputs directly into 3.3V-only inputs without level shifting.

## Validation
- Power-on smoke test passes without overheating.
- Each sensor or actuator responds independently.
- The final workflow matches the intended project purpose.
- The build remains stable for at least 15 minutes of continuous operation.

Revision note: moved to enclosure planning.

## Bill of Materials
- Arduino: qty 1, unit $18.0, total $18.0
- LED strip: qty 1, unit $10.0, total $10.0
- relay module: qty 1, unit $6.0, total $6.0

## Wiring Plan
- Arduino -> LED strip (GPIO / data): Confirm voltage compatibility before connecting LED strip.
- Arduino -> relay module (GPIO / data): Confirm voltage compatibility before connecting relay module.

## Safety Warnings
- Validate current draw before powering motors, relays, or heating elements.
- Do not connect 5V outputs directly into 3.3V-only inputs without level shifting.

## Build Steps
- Review the home automation requirements and confirm the goal: Home automation.
- Lay out the controller, power path, and peripherals before wiring anything.
- Wire one component at a time and test each connection before adding the next part.
- Load a minimal firmware sketch or script to verify communication with each module.
- Integrate the full workflow and test against the main success criteria.

## Testing Checklist
- Power-on smoke test passes without overheating.
- Each sensor or actuator responds independently.
- The final workflow matches the intended project purpose.
- The build remains stable for at least 15 minutes of continuous operation.