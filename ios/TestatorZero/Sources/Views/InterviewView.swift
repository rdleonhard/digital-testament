import SwiftUI

// The curiosity engine, phone-native: the avatar asks one question about
// its own life; you answer by voice or keyboard; the answer becomes a
// memory in the corpus. Banked (pending) questions ask free.

struct InterviewView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var subs: SubscriptionManager
    @State private var question: String?
    @State private var answer = ""
    @State private var busy = false
    @State private var committed: Int?

    var body: some View {
        VStack(spacing: 18) {
            HStack {
                Text("THE INTERVIEW")
                    .font(.system(.subheadline, design: .monospaced))
                    .kerning(2).foregroundStyle(Theme.gold)
                Spacer()
                Text("\(store.corpus?.memories.count ?? 0) memories")
                    .font(.caption).foregroundStyle(Theme.dim)
            }
            .padding(.horizontal, 16).padding(.top, 12)

            Spacer()

            if let q = question {
                Text(q)
                    .font(.title3.weight(.medium))
                    .foregroundStyle(Theme.ink)
                    .multilineTextAlignment(.center)
                    .padding(20)
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16)
                        .stroke(Theme.gold.opacity(0.4)))
                    .padding(.horizontal, 20)

                TextField("answer — this becomes a memory", text: $answer, axis: .vertical)
                    .lineLimit(2 ... 6)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 12))
                    .foregroundStyle(Theme.ink)
                    .padding(.horizontal, 20)

                HStack(spacing: 16) {
                    Button {
                        if voice.listening { voice.stopListening() }
                        else { try? voice.startListening(context: "interview") }
                    } label: {
                        let on = voice.listening && voice.context == "interview"
                        Label(on ? "listening…" : "speak",
                              systemImage: on ? "mic.fill" : "mic")
                            .foregroundStyle(on ? .red : Theme.gold)
                    }
                    Button("Commit memory") { commit(q) }
                        .buttonStyle(.borderedProminent)
                        .disabled(answer.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            } else if let n = committed {
                VStack(spacing: 8) {
                    Image(systemName: "checkmark.seal")
                        .font(.system(size: 40)).foregroundStyle(Theme.gold)
                    Text("Memory #\(n) committed to the corpus.")
                        .foregroundStyle(Theme.ink)
                    Text("The gaps close a little.")
                        .font(.footnote).foregroundStyle(Theme.dim)
                }
            } else {
                Text("The avatar is curious about the life it's inheriting.")
                    .foregroundStyle(Theme.dim)
            }

            Spacer()

            Button {
                Task { await ask() }
            } label: {
                Label("Ask me something", systemImage: "questionmark.bubble")
                    .frame(maxWidth: .infinity).padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .disabled(busy)
            .padding(.horizontal, 20).padding(.bottom, 16)
        }
        .background(Theme.bg)
        .onChange(of: voice.transcript) {
            if voice.listening, voice.context == "interview" { answer = voice.transcript }
        }
    }

    private func ask() async {
        committed = nil
        if let banked = store.popPending() {
            question = banked.question
            store.mood = banked.mood
            if settings.speakReplies { voice.speak(banked.question) }
            return
        }
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subs.subscribed) else {
            question = VeniceError.needsEntitlement.localizedDescription
            return
        }
        busy = true
        defer { busy = false }
        let recent = (store.corpus?.memories ?? [])
            .filter { $0.tags.contains("interview") }
            .suffix(10).map(\.title).joined(separator: "; ")
        let ask = "You feel a gap in your memory. Ask your subject exactly ONE short, specific, warm question about their life — past, present, feelings, or daily texture. Not similar to: \(recent.isEmpty ? "(none yet)" : recent). Output only the question, then the [mood: X] line."
        do {
            let reply = try await VeniceClient.chat(messages: [
                ["role": "system", "content": store.systemPrompt()],
                ["role": "user", "content": ask],
            ], key: key, maxTokens: 120)
            let (q, mood) = CorpusStore.parseTags(reply)
            question = q
            store.mood = mood
            if settings.speakReplies { voice.speak(q) }
        } catch {
            question = nil
            committed = nil
        }
    }

    private func commit(_ q: String) {
        if voice.listening { voice.stopListening() }
        store.addMemory(question: q, answer: answer)
        committed = store.corpus?.memories.count
        question = nil
        answer = ""
    }
}
