import Foundation
import UserNotifications

// The daily ritual: once a day, the avatar reaches out — ideally with a
// question it banked at twilight ("Your avatar wonders: ..."). Local
// notifications only; nothing leaves the phone.

enum NotificationManager {
    static let id = "daily-ritual"

    static func requestAuth() async -> Bool {
        (try? await UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .sound, .badge])) ?? false
    }

    static func scheduleDaily(hour: Int, question: String?, name: String) {
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: [id])
        let content = UNMutableNotificationContent()
        content.title = "The flame is lit"
        if let q = question, !q.isEmpty {
            content.body = "\(name) wonders: \(q)"
        } else {
            content.body = "\(name) is curious about your day. Give it one memory."
        }
        content.sound = .default
        var comps = DateComponents()
        comps.hour = hour
        let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: true)
        center.add(UNNotificationRequest(identifier: id, content: content,
                                         trigger: trigger))
    }

    // Schedule the next N days, one pre-formulated "text" per day, each a
    // distinct nudge — so it reads like your avatar messaging you, not a
    // repeating reminder.
    static func scheduleNudges(_ nudges: [String], hour: Int, name: String) {
        let center = UNUserNotificationCenter.current()
        let ids = (0 ..< 14).map { "\(id)-\($0)" } + [id]
        center.removePendingNotificationRequests(withIdentifiers: ids)
        let cal = Calendar.current
        guard var fire = cal.nextDate(
            after: Date(), matching: DateComponents(hour: hour, minute: 0),
            matchingPolicy: .nextTime) else { return }
        for (i, text) in nudges.prefix(7).enumerated() {
            let content = UNMutableNotificationContent()
            content.title = name
            content.body = text
            content.sound = .default
            let comps = cal.dateComponents([.year, .month, .day, .hour, .minute],
                                           from: fire)
            let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: false)
            center.add(UNNotificationRequest(identifier: "\(id)-\(i)",
                                             content: content, trigger: trigger))
            fire = cal.date(byAdding: .day, value: 1, to: fire) ?? fire
        }
    }

    static func cancel() {
        let ids = (0 ..< 14).map { "\(id)-\($0)" } + [id]
        UNUserNotificationCenter.current()
            .removePendingNotificationRequests(withIdentifiers: ids)
    }
}
