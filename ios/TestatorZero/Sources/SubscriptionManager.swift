import StoreKit
import SwiftUI

// StoreKit 2 subscription: "Remembrance". Digital subscriptions go
// through in-app purchase (Apple's rule); the native sheet charges the
// user's Apple Pay cards. The TestatorZero.storekit config makes the
// full purchase flow work in the simulator with test transactions.

@MainActor
final class SubscriptionManager: ObservableObject {
    static let monthlyID = "zero.remembrance.monthly"
    static let yearlyID = "zero.remembrance.yearly"

    @Published var products: [Product] = []
    @Published var subscribed = false
    @Published var lastError: String?

    private var updates: Task<Void, Never>?

    init() {
        updates = Task { [weak self] in
            for await result in Transaction.updates {
                if case .verified(let t) = result {
                    await t.finish()
                    await self?.refreshEntitlement()
                }
            }
        }
        Task {
            await loadProducts()
            await refreshEntitlement()
        }
    }

    deinit { updates?.cancel() }

    func loadProducts() async {
        do {
            products = try await Product.products(
                for: [Self.monthlyID, Self.yearlyID])
                .sorted { $0.price < $1.price }
        } catch {
            lastError = "Store unavailable: \(error.localizedDescription)"
        }
    }

    func refreshEntitlement() async {
        var active = false
        for await result in Transaction.currentEntitlements {
            if case .verified(let t) = result,
               t.productID == Self.monthlyID || t.productID == Self.yearlyID {
                active = true
            }
        }
        subscribed = active
    }

    func purchase(_ product: Product) async {
        do {
            let result = try await product.purchase()
            if case .success(let verification) = result,
               case .verified(let t) = verification {
                await t.finish()
                await refreshEntitlement()
            }
        } catch {
            lastError = error.localizedDescription
        }
    }

    func restore() async {
        try? await AppStore.sync()
        await refreshEntitlement()
    }
}
