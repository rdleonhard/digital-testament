import Foundation

// The avatar's "texts." Notifications can't call the API at fire time
// (the app isn't running), so we do the opposite of what it looks like:
// while the app IS open we ask the API to formulate a handful of casual,
// attention-grabbing nudges that reference real memories — "Hey,
// whatever happened with…" — bank them, and schedule them as local
// notifications for the days ahead. The question is already formulated;
// the notification just delivers it, sounding exactly like a friend.

@MainActor
enum NudgeEngine {
    // Refill the queue if it's low or stale, then reschedule notifications.
    static func maybeRefill(store: CorpusStore, settings: AppSettings,
                            subscribed: Bool) async {
        guard settings.dailyRitual, let c = store.corpus, c.memories.count >= 2
        else { return }
        let stale = settings.nudgesAt.map { Date().timeIntervalSince($0) > 4 * 86400 } ?? true
        if settings.nudges.count >= 3, !stale {
            reschedule(settings: settings, name: c.identity.preferred_name ?? c.identity.full_name)
            return
        }
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subscribed) else { return }
        let sample = (c.memories.shuffled().prefix(14))
            .map { "\($0.title): \($0.narrative.prefix(150))" }
            .joined(separator: "\n")
        let ask = """
        Here are fragments from a person's life:
        \(sample)

        Write 7 short text-message nudges TO that person, as if from a curious old friend who remembers these things. Each must:
        - reference something SPECIFIC from a fragment
        - sound like a real text ("Hey, whatever happened with…", "I keep thinking about…", "did you ever…")
        - be under 14 words and end with a question mark
        One per line. No numbering, no quotes, no preamble.
        """
        guard let reply = try? await VeniceClient.chat(
            messages: [
                ["role": "system", "content": "You write short, warm, casual text-message nudges. Nothing else."],
                ["role": "user", "content": ask],
            ], key: key, maxTokens: 320) else { return }
        let lines = reply
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: CharacterSet(charactersIn: " \t\"-•*0123456789.")) }
            .filter { $0.count > 8 && $0.count < 130 && !$0.lowercased().contains("[mood") }
        guard !lines.isEmpty else { return }
        settings.nudges = Array(lines.prefix(7))
        settings.nudgesAt = Date()
        reschedule(settings: settings, name: c.identity.preferred_name ?? c.identity.full_name)
    }

    static func reschedule(settings: AppSettings, name: String) {
        if settings.nudges.isEmpty {
            NotificationManager.scheduleDaily(hour: settings.ritualHour,
                                              question: nil, name: name)
        } else {
            NotificationManager.scheduleNudges(settings.nudges,
                                               hour: settings.ritualHour, name: name)
        }
    }
}
