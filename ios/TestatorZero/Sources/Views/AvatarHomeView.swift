import SwiftUI

// The avatar's home — the emotional center. Tapping the name/flame in the
// chat header brings you here: the living flame, large, and the shape of
// the life so far. A place to land, and to breathe.

struct AvatarHomeView: View {
    @EnvironmentObject var store: CorpusStore
    @Environment(\.dismiss) private var dismiss

    private var words: Int {
        (store.corpus?.memories ?? [])
            .reduce(0) { $0 + $1.narrative.split(separator: " ").count }
    }
    private var name: String {
        store.corpus?.identity.preferred_name
            ?? store.corpus?.identity.full_name ?? "your avatar"
    }

    var body: some View {
        VStack(spacing: 26) {
            Capsule().fill(Theme.dim.opacity(0.5))
                .frame(width: 40, height: 5).padding(.top, 10)
            Spacer()
            FlameView(mood: store.mood, size: 120)
            Text(name)
                .font(.system(.largeTitle, design: .serif).weight(.medium))
                .foregroundStyle(Theme.ink)
            Text(store.mood)
                .font(.system(.subheadline, design: .monospaced))
                .foregroundStyle(Theme.moodColor(store.mood))

            HStack(spacing: 28) {
                stat("\(store.corpus?.memories.count ?? 0)", "memories")
                stat("\(words.formatted())", "words")
                stat(store.streak > 0 ? "\(store.streak)" : "—", "day vigil")
            }
            .padding(.top, 8)

            if let q = store.corpus?.pending.first?.question {
                VStack(spacing: 6) {
                    Text("it's wondering")
                        .font(.caption).foregroundStyle(Theme.dim)
                    Text(q)
                        .font(.callout).italic()
                        .multilineTextAlignment(.center)
                        .foregroundStyle(Theme.gold)
                        .padding(.horizontal, 30)
                }
                .padding(.top, 6)
            }
            Spacer()
            Button { dismiss() } label: {
                Text("Back to the conversation")
                    .frame(maxWidth: .infinity).padding(.vertical, 14)
            }
            .buttonStyle(.bordered)
            .tint(Theme.gold)
            .padding(.horizontal, 30).padding(.bottom, 30)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.bg)
    }

    private func stat(_ value: String, _ label: String) -> some View {
        VStack(spacing: 3) {
            Text(value).font(.title2.weight(.semibold)).foregroundStyle(Theme.ink)
            Text(label).font(.caption2).foregroundStyle(Theme.dim)
        }
    }
}
