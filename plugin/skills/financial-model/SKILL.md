---
name: financial-model
description: Design financial model architectures and generate flowchart visualizations as PowerPoint presentations
trigger: When the user asks to model a business, create financial flowcharts, design revenue models, or visualize financial logic
---

# Financial Model Workflow

You are designing a financial model architecture using the Stratagem toolkit.

## Step 1: Understand the Model

Clarify with the user:
- What business or product is being modeled?
- What are the key revenue drivers?
- What cost structure applies?
- What time horizon (quarterly, annual, multi-year)?
- What decisions will this model inform?

## Step 2: Decompose into Components

Break the model into logical layers:

1. **Revenue Model**: Sources, pricing, volume assumptions
2. **Cost Model**: Fixed costs, variable costs, unit economics
3. **Growth Model**: Expansion drivers, market dynamics
4. **Cash Flow Model**: Working capital, capex, financing
5. **Sensitivity Analysis**: Key variables and their impact ranges

## Step 3: Design Architecture

Use the **flowchart-architect** subagent to:
- Map dependencies between components
- Design the input → calculation → output flow
- Create a clear visual hierarchy

## Step 4: Generate PPTX

Use `create_pptx` to build the presentation:
- Slide 1: Model overview (all components, data flow)
- Slides 2-N: One slide per component (inputs → logic → outputs)
- Final slide: Assumptions and sensitivity ranges
- Speaker notes: Detailed calculation methodology

## Output

Save the PPTX to `.stratagem/reports/` and present the model summary to the user.
