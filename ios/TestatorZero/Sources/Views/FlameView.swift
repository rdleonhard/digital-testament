import SwiftUI

// The living flame — the app's soul, animated. Mood tints it; it breathes
// and flickers gently (a vigil, not a campfire). Pure Canvas, cheap.

struct FlameView: View {
    var mood: String = "curious"
    var size: CGFloat = 28

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
            let t = timeline.date.timeIntervalSinceReferenceDate
            Canvas { ctx, sz in
                let w = sz.width, h = sz.height
                let flick = 0.06 * sin(t * 5.1) + 0.04 * sin(t * 8.7 + 1.3)
                let sway = 0.05 * sin(t * 3.3) + 0.03 * sin(t * 6.1 + 0.7)
                let tint = Theme.moodColor(mood)

                func flame(scale: CGFloat, dx: CGFloat, color: Color, blur: CGFloat) {
                    var p = Path()
                    let cx = w * 0.5 + w * dx * sway
                    let tipY = h * (0.06 + 0.05 * flick) + h * (1 - scale) * 0.42
                    let baseY = h * 0.94
                    let belly = w * 0.34 * scale * (1 + flick * 0.5)
                    p.move(to: CGPoint(x: cx, y: tipY))
                    p.addCurve(to: CGPoint(x: cx + belly, y: h * 0.58),
                               control1: CGPoint(x: cx + belly * 0.5, y: tipY + h * 0.16),
                               control2: CGPoint(x: cx + belly, y: h * 0.40))
                    p.addQuadCurve(to: CGPoint(x: cx, y: baseY),
                                   control: CGPoint(x: cx + belly * 0.9, y: h * 0.86))
                    p.addQuadCurve(to: CGPoint(x: cx - belly, y: h * 0.58),
                                   control: CGPoint(x: cx - belly * 0.9, y: h * 0.86))
                    p.addCurve(to: CGPoint(x: cx, y: tipY),
                               control1: CGPoint(x: cx - belly, y: h * 0.40),
                               control2: CGPoint(x: cx - belly * 0.5, y: tipY + h * 0.16))
                    var c = ctx
                    if blur > 0 { c.addFilter(.blur(radius: blur)) }
                    c.fill(p, with: .color(color))
                }

                flame(scale: 1.18, dx: 0.10, color: tint.opacity(0.35), blur: size * 0.16)
                flame(scale: 1.0, dx: 0.10, color: tint, blur: 0)
                flame(scale: 0.55, dx: 0.16, color: Color(red: 1, green: 0.96, blue: 0.84), blur: size * 0.03)
            }
            .frame(width: size, height: size * 1.25)
        }
        .accessibilityHidden(true)
    }
}
