import StoreKit
import SwiftUI

struct PaywallView: View {
    @EnvironmentObject var subs: SubscriptionManager

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "infinity")
                .font(.system(size: 44))
                .foregroundStyle(Theme.gold)
            Text("Remembrance")
                .font(.title.weight(.semibold))
                .foregroundStyle(Theme.ink)
            Text("Your subscription buys your avatar its daily thinking — private inference, no ads, no training on your life. Cancel anytime; your corpus is yours and exports free, forever.")
                .multilineTextAlignment(.center)
                .foregroundStyle(Theme.dim)
                .padding(.horizontal, 28)

            ForEach(subs.products, id: \.id) { product in
                Button {
                    Task { await subs.purchase(product) }
                } label: {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(product.displayName).font(.headline)
                            Text(product.description)
                                .font(.caption).foregroundStyle(Theme.dim)
                        }
                        Spacer()
                        Text(product.displayPrice).font(.title3.weight(.semibold))
                    }
                    .padding(16)
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 14))
                    .overlay(RoundedRectangle(cornerRadius: 14)
                        .stroke(Theme.gold.opacity(0.35)))
                }
                .foregroundStyle(Theme.ink)
                .padding(.horizontal, 24)
            }

            if subs.products.isEmpty {
                ProgressView().tint(Theme.gold)
                Text(subs.lastError ?? "Loading plans…")
                    .font(.footnote).foregroundStyle(Theme.dim)
            }

            Button("Restore purchases") { Task { await subs.restore() } }
                .font(.footnote)
                .foregroundStyle(Theme.dim)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.bg)
    }
}
