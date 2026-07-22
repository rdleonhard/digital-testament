import SwiftUI

// The corpus itself: every memory (tap to expand), a direct "write a
// memory" composer, swipe-to-delete, and the export that makes this app
// a feeder for the Testament Network rather than a walled garden. The
// exported JSON is the standard Digital Corpus.

struct MemoriesView: View {
    @EnvironmentObject var store: CorpusStore
    @State private var expanded: Set<String> = []
    @State private var composing = false

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

    private var stats: (words: Int, kinds: [(String, Int)]) {
        let mems = store.corpus?.memories ?? []
        let words = mems.reduce(0) { $0 + $1.narrative.split(separator: " ").count }
        var counts: [String: Int] = [:]
        for m in mems { for t in m.tags { counts[t, default: 0] += 1 } }
        return (words, counts.sorted { $0.value > $1.value })
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack(spacing: 14) {
                        FlameView(mood: store.mood, size: 34)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(store.streak > 1 ? "\(store.streak)-day vigil" : "The vigil begins")
                                .font(.headline).foregroundStyle(Theme.gold)
                            Text("\(store.corpus?.memories.count ?? 0) memories · \(stats.words.formatted()) words of a life")
                                .font(.caption).foregroundStyle(Theme.dim)
                            Text(stats.kinds.prefix(4)
                                    .map { "\($0.1) \($0.0)" }.joined(separator: " · "))
                                .font(.caption2).foregroundStyle(Theme.dim)
                        }
                        Spacer()
                    }
                    .padding(.vertical, 4)
                    .listRowBackground(Theme.panel)
                }
                Section {
                    ForEach((store.corpus?.memories ?? []).reversed()) { m in
                        MemoryRow(memory: m, expanded: expanded.contains(m.id))
                            .contentShape(Rectangle())
                            .onTapGesture {
                                Haptics.tap()
                                if expanded.contains(m.id) { expanded.remove(m.id) }
                                else { expanded.insert(m.id) }
                            }
                            .contextMenu {
                                if let img = MemoryCard.render(memory: m,
                                        name: store.corpus?.identity.preferred_name ?? "") {
                                    ShareLink(item: Image(uiImage: img),
                                              preview: SharePreview(m.title,
                                                                    image: Image(uiImage: img))) {
                                        Label("Share as card", systemImage: "square.and.arrow.up")
                                    }
                                }
                            }
                            .listRowBackground(Theme.panel)
                    }
                    .onDelete { idxs in
                        let shown = (store.corpus?.memories ?? []).reversed().map { $0 }
                        for i in idxs { store.deleteMemory(shown[i]) }
                    }
                } header: {
                    Text("\(store.corpus?.pending.count ?? 0) questions waiting · long-press to share")
                        .foregroundStyle(Theme.dim)
                } footer: {
                    Text("Tap a memory to read it in full, swipe to delete. Your corpus is yours — export it any time; it's the same Digital Corpus the Testament Network deploys to self-hosted nodes, agent runtimes, and, one day, the device your will hands to your executor.")
                        .foregroundStyle(Theme.dim)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.bg)
            .navigationTitle("Corpus")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { composing = true } label: {
                        Label("Write", systemImage: "square.and.pencil")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    if let url = exportURL {
                        ShareLink(item: url) {
                            Label("Export", systemImage: "square.and.arrow.up")
                        }
                    }
                }
            }
            .sheet(isPresented: $composing) { ComposeMemoryView() }
        }
    }
}

struct MemoryRow: View {
    let memory: Memory
    let expanded: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(memory.title).font(.subheadline.weight(.medium))
                    .foregroundStyle(Theme.ink)
                    .lineLimit(expanded ? nil : 1)
                Spacer()
                ForEach(memory.tags, id: \.self) { t in
                    Text(t).font(.caption2)
                        .padding(.horizontal, 7).padding(.vertical, 2)
                        .background(Theme.gold.opacity(0.15), in: Capsule())
                        .foregroundStyle(Theme.gold)
                }
            }
            Text(memory.narrative).font(.footnote)
                .foregroundStyle(Theme.dim)
                .lineLimit(expanded ? nil : 3)
            if !expanded, memory.narrative.count > 160 {
                Text("tap to read")
                    .font(.caption2).foregroundStyle(Theme.gold.opacity(0.7))
            }
        }
        .animation(.easeInOut(duration: 0.15), value: expanded)
    }
}

struct ComposeMemoryView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var body_ = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Title (optional)") {
                    TextField("A name for this memory", text: $title)
                        .foregroundStyle(Theme.ink)
                }
                Section {
                    TextField("Write it in your own words…", text: $body_, axis: .vertical)
                        .lineLimit(5 ... 14)
                        .foregroundStyle(Theme.ink)
                    Button {
                        if voice.listening { voice.stopListening() }
                        else { try? voice.startListening(context: "compose") }
                    } label: {
                        let on = voice.listening && voice.context == "compose"
                        Label(on ? "listening…" : "dictate",
                              systemImage: on ? "mic.fill" : "mic")
                            .foregroundStyle(on ? .red : Theme.gold)
                    }
                } header: { Text("The memory") }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.bg)
            .navigationTitle("Write a memory")
            .navigationBarTitleDisplayMode(.inline)
            .onChange(of: voice.transcript) {
                if voice.listening, voice.context == "compose" { body_ = voice.transcript }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { voice.stopListening(); dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        voice.stopListening()
                        store.commitMemory(title: title, narrative: body_)
                        dismiss()
                    }
                    .disabled(body_.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}
