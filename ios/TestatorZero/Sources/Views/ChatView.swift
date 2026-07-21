import SwiftUI

struct Bubble: Identifiable {
    let id = UUID()
    let text: String
    let mine: Bool
}

struct ChatView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @State private var bubbles: [Bubble] = []
    @State private var draft = ""
    @State private var busy = false

    var body: some View {
        VStack(spacing: 0) {
            header
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(bubbles) { b in
                            HStack {
                                if b.mine { Spacer(minLength: 40) }
                                Text(b.text)
                                    .padding(12)
                                    .background(
                                        b.mine ? Color(red: 0.12, green: 0.23, blue: 0.37)
                                               : Theme.panel,
                                        in: RoundedRectangle(cornerRadius: 12))
                                    .foregroundStyle(Theme.ink)
                                if !b.mine { Spacer(minLength: 40) }
                            }
                            .id(b.id)
                        }
                        if busy { ProgressView().tint(Theme.gold).padding(.leading, 12) }
                    }
                    .padding(14)
                }
                .onChange(of: bubbles.count) {
                    if let last = bubbles.last { proxy.scrollTo(last.id, anchor: .bottom) }
                }
            }
            inputBar
        }
        .background(Theme.bg)
        .onChange(of: voice.transcript) {
            if voice.listening { draft = voice.transcript }
        }
    }

    private var header: some View {
        HStack {
            Text((store.corpus?.identity.preferred_name ?? "avatar").uppercased())
                .font(.system(.subheadline, design: .monospaced))
                .kerning(2)
                .foregroundStyle(Theme.gold)
            Spacer()
            Circle().fill(Theme.moodColor(store.mood)).frame(width: 9, height: 9)
            Text(store.mood).font(.caption).foregroundStyle(Theme.dim)
            if voice.speaking {
                Image(systemName: "speaker.wave.2.fill")
                    .font(.caption).foregroundStyle(Theme.gold)
            }
        }
        .padding(.horizontal, 16).padding(.vertical, 10)
        .background(Theme.panel)
    }

    private var inputBar: some View {
        HStack(spacing: 10) {
            TextField("say something…", text: $draft, axis: .vertical)
                .lineLimit(1 ... 3)
                .textFieldStyle(.plain)
                .padding(10)
                .background(Theme.panel, in: RoundedRectangle(cornerRadius: 10))
                .foregroundStyle(Theme.ink)
            Button {
                if voice.listening {
                    voice.stopListening()
                } else {
                    try? voice.startListening()
                }
            } label: {
                Image(systemName: voice.listening ? "mic.fill" : "mic")
                    .font(.title3)
                    .foregroundStyle(voice.listening ? .red : Theme.gold)
            }
            Button { Task { await send() } } label: {
                Image(systemName: "arrow.up.circle.fill").font(.title2)
            }
            .disabled(busy || draft.trimmingCharacters(in: .whitespaces).isEmpty)
        }
        .padding(12)
        .background(Theme.bg)
    }

    private func send() async {
        if voice.listening { voice.stopListening() }
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        draft = ""
        bubbles.append(Bubble(text: text, mine: true))
        busy = true
        defer { busy = false }
        do {
            let reply = try await VeniceClient.chat(messages: [
                ["role": "system", "content": store.systemPrompt()],
                ["role": "user", "content": text],
            ])
            let (clean, mood) = CorpusStore.parseTags(reply)
            store.mood = mood
            bubbles.append(Bubble(text: clean, mine: false))
            voice.speak(clean)
        } catch {
            bubbles.append(Bubble(text: "(\(error.localizedDescription))", mine: false))
        }
    }
}
