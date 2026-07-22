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

    static func cancel() {
        UNUserNotificationCenter.current()
            .removePendingNotificationRequests(withIdentifiers: [id])
    }
}
