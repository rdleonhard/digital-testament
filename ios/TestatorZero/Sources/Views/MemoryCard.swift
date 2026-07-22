import SwiftUI

// A shareable gold-on-black memory card — the app's organic marketing.
// People post their avatar's reflections; the footer carries the name.

struct MemoryCardView: View {
    let memory: Memory
    let name: String

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                FlameStatic()
                Spacer()
                Text(memory.tags.first ?? "memory")
                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                    .foregroundStyle(Theme.gold)
            }
            Text(memory.title)
                .font(.system(size: 24, weight: .medium, design: .serif))
                .foregroundStyle(Theme.ink)
            Text(memory.narrative)
                .font(.system(size: 16, design: .serif))
                .foregroundStyle(Theme.ink.opacity(0.85))
                .lineSpacing(5)
                .lineLimit(12)
            Spacer(minLength: 8)
            HStack {
                Text(name.isEmpty ? "TESTATOR ZERO" : "\(name.uppercased()) · TESTATOR ZERO")
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .kerning(1.5)
                    .foregroundStyle(Theme.gold.opacity(0.8))
                Spacer()
            }
        }
        .padding(30)
        .frame(width: 420, height: 540, alignment: .topLeading)
        .background(Theme.bg)
        .overlay(RoundedRectangle(cornerRadius: 0)
            .strokeBorder(Theme.gold.opacity(0.35), lineWidth: 1.5)
            .padding(9))
    }
}

// A still flame for rendering (Canvas timelines don't render offscreen).
struct FlameStatic: View {
    var body: some View {
        Image(systemName: "flame.fill")
            .font(.system(size: 22))
            .foregroundStyle(Theme.gold)
    }
}

@MainActor
enum MemoryCard {
    static func render(memory: Memory, name: String) -> UIImage? {
        let renderer = ImageRenderer(
            content: MemoryCardView(memory: memory, name: name))
        renderer.scale = 3
        return renderer.uiImage
    }
}
