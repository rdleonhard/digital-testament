import SwiftUI

struct Bubble: Identifiable {
    let id = UUID()
    let text: String
    let mine: Bool
}

struct ChatView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var subs: SubscriptionManager
    @State private var bubbles: [Bubble] = []
    @State private var draft = ""
    @State private var busy = false
    @State private var showHome = false
    @FocusState private var focused: Bool

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
                .scrollDismissesKeyboard(.interactively)
                .contentShape(Rectangle())
                .onTapGesture { focused = false; hideKeyboard() }
            }
            inputBar
        }
        .sheet(isPresented: $showHome) {
            AvatarHomeView().presentationDragIndicator(.hidden)
        }
        .background(Theme.bg)
        .onAppear {
            if bubbles.isEmpty, let c = store.corpus {
                let n = c.identity.preferred_name ?? c.identity.full_name
                bubbles.append(Bubble(
                    text: "\(n) is awake — \(c.memories.count) memories aboard. Ask me about my life, or tell me something I don't know yet.",
                    mine: false))
            }
        }
        .onChange(of: voice.transcript) {
            if voice.listening, voice.context == "chat" { draft = voice.transcript }
        }
    }

    private var header: some View {
        Button {
            focused = false; hideKeyboard()
            Haptics.tap()
            showHome = true
        } label: {
            HStack(spacing: 10) {
                FlameView(mood: store.mood, size: 20)
                Text((store.corpus?.identity.preferred_name ?? "avatar").uppercased())
                    .font(.system(.subheadline, design: .monospaced))
                    .kerning(2)
                    .foregroundStyle(Theme.gold)
                Image(systemName: "chevron.down").font(.caption2).foregroundStyle(Theme.dim)
                Spacer()
                Text(store.mood).font(.caption).foregroundStyle(Theme.dim)
                if voice.speaking {
                    Image(systemName: "speaker.wave.2.fill")
                        .font(.caption).foregroundStyle(Theme.gold)
                }
            }
            .contentShape(Rectangle())
            .padding(.horizontal, 16).padding(.vertical, 8)
            .background(Theme.panel)
        }
        .buttonStyle(.plain)
    }

    private var inputBar: some View {
        HStack(spacing: 10) {
            TextField("say something…", text: $draft, axis: .vertical)
                .lineLimit(1 ... 3)
                .textFieldStyle(.plain)
                .focused($focused)
                .padding(10)
                .background(Theme.panel, in: RoundedRectangle(cornerRadius: 10))
                .foregroundStyle(Theme.ink)
            Button {
                if voice.listening {
                    voice.stopListening()
                } else {
                    try? voice.startListening(context: "chat")
                }
            } label: {
                Image(systemName: voice.listening && voice.context == "chat" ? "mic.fill" : "mic")
                    .font(.title3)
                    .foregroundStyle(voice.listening && voice.context == "chat" ? .red : Theme.gold)
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
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subs.subscribed) else {
            bubbles.append(Bubble(text: VeniceError.needsEntitlement.localizedDescription, mine: false))
            return
        }
        draft = ""
        bubbles.append(Bubble(text: text, mine: true))
        busy = true
        defer { busy = false }
        do {
            let reply = try await VeniceClient.chat(messages: [
                ["role": "system", "content": store.systemPrompt()],
                ["role": "user", "content": text],
            ], key: key)
            let (clean, mood) = CorpusStore.parseTags(reply)
            store.mood = mood
            bubbles.append(Bubble(text: clean, mine: false))
            if settings.speakReplies { voice.speak(clean) }
        } catch {
            bubbles.append(Bubble(text: "(\(error.localizedDescription))", mine: false))
        }
    }
}
