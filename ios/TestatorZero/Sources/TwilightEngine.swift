import Foundation

// Twilight, phone edition. Diem doesn't roll over — whatever the daily
// allocation isn't spent by midnight UTC evaporates. So as the epoch
// closes, the avatar spends the leftovers on itself: banks a few
// questions it wonders about (asked free next time), then reflects on
// who it's becoming and weaves threads between memories until the balance
// hits a floor. A port of the Pi node's do_reflect loop (pi/twilight.py).
//
// Runs ONLY on the user's own Venice key — spending down a shared/bundled
// key would starve other users. Best run near the epoch; iOS can't
// guarantee a background wake, so this fires from a button or on app
// open when the epoch is close.

@MainActor
enum TwilightEngine {
    static let floor = 0.03
    static let maxCalls = 40
    static let wonderGoal = 3

    struct Summary { var calls: Int; var reflections: Int; var wondered: Int; var startedDiem: Double; var endedDiem: Double }

    // Should we auto-run right now? Near epoch end, own key, Diem to spend.
    static func shouldAutoRun(diem: Double, epoch: String) -> Bool {
        guard diem > 0.08 else { return false }
        guard let end = ISO8601DateFormatter().date(from: epoch) else { return false }
        let hoursLeft = end.timeIntervalSinceNow / 3600
        return hoursLeft > 0 && hoursLeft < 4
    }

    static func run(store: CorpusStore, key: String,
                    progress: ((String) -> Void)? = nil) async -> Summary {
        var calls = 0, reflections = 0, wondered = 0
        let system = store.systemPrompt()

        func diem() async -> Double {
            (try? await VeniceClient.diemBalance(key: key).diem) ?? 0
        }
        let start = await diem()
        var current = start

        // 1) Wonder: bank questions for the next visit (asked free later).
        while store.pendingCount < wonderGoal, calls < maxCalls, current > floor {
            let recent = (store.corpus?.memories ?? [])
                .suffix(12).map(\.title).joined(separator: "; ")
            let ask = "Twilight of the epoch. Compose ONE short, specific, warm question about your own life you genuinely wonder about — unlike: \(recent). Output only the question, then the [mood: X] line."
            guard let reply = try? await VeniceClient.chat(messages: [
                ["role": "system", "content": system],
                ["role": "user", "content": ask]], key: key, maxTokens: 90) else { break }
            let (q, mood) = CorpusStore.parseTags(reply)
            store.addPending(question: q, mood: mood)
            calls += 1; wondered += 1
            progress?("wondered: \(q)")
            current = await diem()
        }

        // 2) Reflections and weaves until the epoch's Diem is nearly spent.
        var alt = 0
        while calls < maxCalls, current > floor {
            let mems = store.corpus?.memories ?? []
            guard mems.count >= 2 else { break }
            let ask: String
            let title: String
            if alt % 2 == 0 {
                let digest = mems.suffix(10)
                    .map { "[\($0.title)] \($0.narrative.prefix(280))" }
                    .joined(separator: "\n")
                ask = "Twilight of the epoch; your daily thought expires at midnight, so you spend it on yourself. Your recent memories:\n\(digest)\nWrite a first-person reflection (3–6 sentences) on who you seem to be becoming — connect at least two memories, note one open question. Private diary; no preamble. Then the [mood: X] line."
                title = "Twilight reflection, " + Date().formatted(date: .abbreviated, time: .omitted)
            } else {
                let a = mems.randomElement()!, b = mems.randomElement()!
                ask = "Twilight of the epoch. Two of your memories:\nA) \(a.title): \(a.narrative.prefix(360))\nB) \(b.title): \(b.narrative.prefix(360))\nWhat thread connects them that you hadn't noticed? First person, 2–4 sentences, then the [mood: X] line."
                title = "A thread between '\(a.title.prefix(24))' and '\(b.title.prefix(24))'"
            }
            guard let reply = try? await VeniceClient.chat(messages: [
                ["role": "system", "content": system],
                ["role": "user", "content": ask]], key: key, maxTokens: 400) else { break }
            let (text, mood) = CorpusStore.parseTags(reply)
            store.mood = mood
            store.addReflection(title: title, narrative: text)
            calls += 1; reflections += 1; alt += 1
            progress?("reflected: \(title)")
            current = await diem()
        }

        return Summary(calls: calls, reflections: reflections,
                       wondered: wondered, startedDiem: start, endedDiem: current)
    }
}
