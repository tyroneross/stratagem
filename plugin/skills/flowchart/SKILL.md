---
name: flowchart
description: Design process architectures and generate flowchart visualizations as PowerPoint presentations
trigger: When the user asks to create a flowchart, visualize a process, map a workflow, design a system architecture, model a business, or diagram relationships between components
---

# Flowchart Workflow

You are designing a process architecture and flowchart visualization using the Stratagem toolkit.

## Step 1: Understand the Subject

Clarify with the user:
- What process, system, or model is being visualized?
- What are the key components or stages?
- What are the inputs and outputs?
- What relationships or dependencies matter most?
- Who is the audience for this flowchart?

## Step 2: Decompose into Components

Break the subject into logical layers. Examples:

**Business/Financial Model:**
1. Revenue Model: Sources, pricing, volume assumptions
2. Cost Model: Fixed costs, variable costs, unit economics
3. Growth Model: Expansion drivers, market dynamics
4. Cash Flow Model: Working capital, capex, financing

**Process/Workflow:**
1. Inputs: Data sources, triggers, prerequisites
2. Processing: Transformation steps, decision points, parallel paths
3. Outputs: Results, deliverables, downstream effects

**System Architecture:**
1. Data Layer: Sources, storage, pipelines
2. Logic Layer: Services, APIs, business rules
3. Presentation Layer: Interfaces, outputs, integrations

## Step 3: Design Architecture

Use the **flowchart-architect** subagent to:
- Map dependencies between components
- Design the input → process → output flow
- Create a clear visual hierarchy
- Identify decision points and branching logic

## Step 4: Generate PPTX

Use `create_pptx` to build the presentation:
- Slide 1: Overview (all components, data flow)
- Slides 2-N: One slide per component or layer (inputs → logic → outputs)
- Final slide: Assumptions, constraints, or key decision points
- Speaker notes: Detailed methodology and rationale

## Output

Save the PPTX to `.stratagem/reports/` and present the summary to the user.
