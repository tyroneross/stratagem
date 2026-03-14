import SwiftUI

struct FlowDiagramView: View {
    let activeAgents: Set<String>
    let completedAgents: Set<String>
    let isRunning: Bool

    @StateObject private var viewModel = FlowDiagramViewModel()

    private let phases: [AgentPhase] = [.planning, .execution, .quality, .delivery]

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0/30.0, paused: !isRunning)) { timeline in
            Canvas { context, size in
                let time = timeline.date.timeIntervalSinceReferenceDate
                drawDiagram(context: context, size: size, time: time)
            }
        }
        .onChange(of: activeAgents) { _, newValue in
            viewModel.updateFromSets(active: newValue, completed: completedAgents)
        }
        .onChange(of: completedAgents) { _, newValue in
            viewModel.updateFromSets(active: activeAgents, completed: newValue)
        }
    }

    private func drawDiagram(context: GraphicsContext, size: CGSize, time: Double) {
        let padding: CGFloat = 16
        let phaseGap: CGFloat = 12
        let arrowWidth: CGFloat = 24

        // Calculate phase column widths proportional to agent count
        let totalArrowWidth = arrowWidth * CGFloat(phases.count - 1)
        let availableWidth = size.width - padding * 2 - totalArrowWidth - phaseGap * CGFloat(phases.count - 1)

        // Weight columns by agent count (min 1)
        let agentCounts = phases.map { phase in max(AgentNode.agentsForPhase(phase).count, 1) }
        let totalWeight = agentCounts.reduce(0, +)
        let columnWidths = agentCounts.map { count in availableWidth * CGFloat(count) / CGFloat(totalWeight) }

        // Minimum column width
        let minColumnWidth: CGFloat = 100
        let adjustedWidths = columnWidths.map { max($0, minColumnWidth) }

        let headerHeight: CGFloat = 24
        let nodeHeight: CGFloat = 28
        let nodeSpacing: CGFloat = 6
        let nodePadding: CGFloat = 8

        var xOffset = padding
        var phaseRects: [CGRect] = []

        for (phaseIndex, phase) in phases.enumerated() {
            let agents = viewModel.nodes.filter { $0.phase == phase }
            let colWidth = adjustedWidths[phaseIndex]
            let contentHeight = headerHeight + CGFloat(agents.count) * (nodeHeight + nodeSpacing) + nodePadding
            let colHeight = min(contentHeight, size.height - padding * 2)

            let colRect = CGRect(x: xOffset, y: padding, width: colWidth, height: colHeight)
            phaseRects.append(colRect)

            // Phase column background
            let columnPath = RoundedRectangle(cornerRadius: 8).path(in: colRect)
            context.fill(columnPath, with: .color(Theme.Color.surface.opacity(0.5)))
            context.stroke(columnPath, with: .color(Theme.Color.border), lineWidth: 1)

            // Phase label
            let labelText = Text(phase.rawValue)
                .font(.system(size: 10, weight: .semibold, design: .default))
                .foregroundColor(Theme.Color.textMuted)
            context.draw(
                context.resolve(labelText),
                at: CGPoint(x: colRect.midX, y: colRect.minY + 14),
                anchor: .center
            )

            // Agent nodes
            for (agentIndex, agent) in agents.enumerated() {
                let nodeY = colRect.minY + headerHeight + CGFloat(agentIndex) * (nodeHeight + nodeSpacing) + nodePadding / 2
                let nodeRect = CGRect(
                    x: colRect.minX + nodePadding,
                    y: nodeY,
                    width: colWidth - nodePadding * 2,
                    height: nodeHeight
                )

                drawNode(context: context, rect: nodeRect, agent: agent, time: time)
            }

            // Flow arrow to next phase
            if phaseIndex < phases.count - 1 {
                let arrowStartX = xOffset + colWidth
                let arrowEndX = arrowStartX + phaseGap + arrowWidth
                let arrowY = size.height / 2

                let hasActiveInPhase = agents.contains { $0.state == .active }
                let allCompletedInPhase = agents.allSatisfy { $0.state == .completed }

                drawArrow(
                    context: context,
                    from: CGPoint(x: arrowStartX + 4, y: arrowY),
                    to: CGPoint(x: arrowEndX - 4, y: arrowY),
                    isActive: hasActiveInPhase,
                    isCompleted: allCompletedInPhase,
                    time: time
                )
            }

            xOffset += colWidth + phaseGap + arrowWidth
        }
    }

    private func drawNode(context: GraphicsContext, rect: CGRect, agent: AgentNode, time: Double) {
        let fillColor: Color
        let strokeColor: Color
        let textColor: Color
        var strokeWidth: CGFloat = 1

        switch agent.state {
        case .idle:
            fillColor = Theme.Color.nodeIdleFill
            strokeColor = Theme.Color.nodeIdleStroke
            textColor = Theme.Color.nodeIdleText
        case .active:
            fillColor = Theme.Color.nodeActiveFill
            strokeColor = Theme.Color.nodeActiveStroke
            textColor = Theme.Color.nodeActiveText
            // Pulse effect: oscillate stroke width
            let pulse = sin(time * 3.0) * 0.5 + 0.5 // 0 to 1
            strokeWidth = 1.5 + CGFloat(pulse) * 1.5
        case .completed:
            fillColor = Theme.Color.nodeCompletedFill
            strokeColor = Theme.Color.nodeCompletedStroke
            textColor = Theme.Color.nodeCompletedText
        }

        let nodePath = RoundedRectangle(cornerRadius: 6).path(in: rect)
        context.fill(nodePath, with: .color(fillColor))
        context.stroke(nodePath, with: .color(strokeColor), lineWidth: strokeWidth)

        // Agent name
        let nameText = Text(agent.displayName)
            .font(.system(size: 11, weight: agent.state == .active ? .semibold : .regular))
            .foregroundColor(textColor)
        context.draw(
            context.resolve(nameText),
            at: CGPoint(x: rect.midX, y: rect.midY),
            anchor: .center
        )
    }

    private func drawArrow(context: GraphicsContext, from: CGPoint, to: CGPoint, isActive: Bool, isCompleted: Bool, time: Double) {
        var path = Path()
        path.move(to: from)
        path.addLine(to: to)

        let arrowColor: Color
        var lineWidth: CGFloat = 1

        if isCompleted {
            arrowColor = Theme.Color.nodeCompletedStroke
            lineWidth = 1.5
        } else if isActive {
            arrowColor = Theme.Color.nodeActiveStroke
            lineWidth = 1.5
        } else {
            arrowColor = Theme.Color.border
        }

        if isActive {
            // Animated dash pattern
            let dashOffset = CGFloat(time.truncatingRemainder(dividingBy: 1.0)) * 16
            let style = StrokeStyle(lineWidth: lineWidth, dash: [6, 4], dashPhase: dashOffset)
            context.stroke(path, with: .color(arrowColor), style: style)
        } else {
            context.stroke(path, with: .color(arrowColor), lineWidth: lineWidth)
        }

        // Arrowhead
        let headSize: CGFloat = 6
        var headPath = Path()
        headPath.move(to: to)
        headPath.addLine(to: CGPoint(x: to.x - headSize, y: to.y - headSize / 2))
        headPath.addLine(to: CGPoint(x: to.x - headSize, y: to.y + headSize / 2))
        headPath.closeSubpath()
        context.fill(headPath, with: .color(arrowColor))
    }
}
