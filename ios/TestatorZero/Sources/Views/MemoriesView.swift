import SwiftUI

// The corpus itself: every memory, and the export that makes this app a
// feeder for the Testament Network rather than a walled garden. The
// exported JSON is the standard Digital Corpus — deployable to a node,
// an ElizaOS character, or a Testament Key by the estate.

struct MemoriesView: View {
    @EnvironmentObject var store: CorpusStore

    private var exportURL: URL? {
        guard let c = store.corpus else { return nil }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        guard let data = try? enc.encode(c) else { return nil }
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("corpus-export.json")
        try? data.write(to: url)
        return url
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach((store.corpus?.memories ?? []).reversed()) { m in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(m.title).font(.subheadline.weight(.medium))
                                    .foregroundStyle(Theme.ink)
                                Spacer()
                                ForEach(m.tags, id: \.self) { t in
                                    Text(t).font(.caption2)
                                        .padding(.horizontal, 7).padding(.vertical, 2)
                                        .background(Theme.gold.opacity(0.15),
                                                    in: Capsule())
                                        .foregroundStyle(Theme.gold)
                                }
                            }
                            Text(m.narrative).font(.footnote)
                                .foregroundStyle(Theme.dim).lineLimit(4)
                        }
                        .listRowBackground(Theme.panel)
                    }
                } header: {
                    Text("\(store.corpus?.memories.count ?? 0) memories · \(store.corpus?.pending.count ?? 0) questions waiting")
                        .foregroundStyle(Theme.dim)
                } footer: {
                    Text("Your corpus is yours. Export it any time — it is the same Digital Corpus the Testament Network deploys to self-hosted nodes, agent runtimes, and, one day, the device your will hands to your executor.")
                        .foregroundStyle(Theme.dim)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.bg)
            .navigationTitle("Corpus")
            .toolbar {
                if let url = exportURL {
                    ShareLink(item: url) {
                        Label("Export", systemImage: "square.and.arrow.up")
                    }
                }
            }
        }
    }
}
