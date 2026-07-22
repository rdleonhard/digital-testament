import PhotosUI
import SwiftUI
import UIKit

// The eye, phone-native: point the camera at a moment; the avatar
// describes what it sees in its own voice and keeps ONLY the words as an
// observation memory. The image is discarded — impressions, not footage.
// (Simulator has no camera; the photo picker stands in there.)

struct ObserveView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var subs: SubscriptionManager
    @State private var showCamera = false
    @State private var pickerItem: PhotosPickerItem?
    @State private var busy = false
    @State private var lastObservation: String?

    private var cameraAvailable: Bool {
        UIImagePickerController.isSourceTypeAvailable(.camera)
    }

    var body: some View {
        VStack(spacing: 18) {
            HStack {
                Text("THE EYE")
                    .font(.system(.subheadline, design: .monospaced))
                    .kerning(2).foregroundStyle(Theme.gold)
                Spacer()
            }
            .padding(.horizontal, 16).padding(.top, 12)

            Spacer()

            if busy {
                ProgressView("the avatar is looking…").tint(Theme.gold)
                    .foregroundStyle(Theme.dim)
            } else if let obs = lastObservation {
                ScrollView {
                    Text(obs)
                        .foregroundStyle(Theme.ink)
                        .padding(18)
                        .background(Theme.panel, in: RoundedRectangle(cornerRadius: 16))
                        .overlay(RoundedRectangle(cornerRadius: 16)
                            .stroke(Theme.gold.opacity(0.4)))
                        .padding(.horizontal, 20)
                }
                Text("kept as words only — the image is gone")
                    .font(.footnote).foregroundStyle(Theme.dim)
            } else {
                Image(systemName: "eye")
                    .font(.system(size: 44)).foregroundStyle(Theme.gold.opacity(0.6))
                Text("Show the avatar a moment of your life.\nIt keeps its impression, never the picture.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Theme.dim)
            }

            Spacer()

            Group {
                if cameraAvailable {
                    Button { showCamera = true } label: {
                        Label("Open the eye", systemImage: "camera")
                            .frame(maxWidth: .infinity).padding(.vertical, 14)
                    }
                } else {
                    PhotosPicker(selection: $pickerItem, matching: .images) {
                        Label("Open the eye (photo picker — no camera here)",
                              systemImage: "photo")
                            .frame(maxWidth: .infinity).padding(.vertical, 14)
                    }
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(busy)
            .padding(.horizontal, 20).padding(.bottom, 16)
        }
        .background(Theme.bg)
        .fullScreenCover(isPresented: $showCamera) {
            CameraPicker { image in
                showCamera = false
                if let img = image { Task { await observe(img) } }
            }
            .ignoresSafeArea()
        }
        .onChange(of: pickerItem) {
            guard let item = pickerItem else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let img = UIImage(data: data) {
                    await observe(img)
                }
                pickerItem = nil
            }
        }
    }

    private func observe(_ image: UIImage) async {
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subs.subscribed) else {
            lastObservation = VeniceError.needsEntitlement.localizedDescription
            return
        }
        busy = true
        defer { busy = false }
        do {
            let reply = try await VeniceClient.describe(
                image: image, systemPrompt: store.systemPrompt(), key: key)
            let (text, mood) = CorpusStore.parseTags(reply)
            store.mood = mood
            lastObservation = text
            let stamp = Date().formatted(date: .abbreviated, time: .shortened)
            store.addMemory(question: "Through my eye, \(stamp)",
                            answer: text, tag: "observation")
            if settings.speakReplies { voice.speak(text) }
        } catch {
            lastObservation = "(\(error.localizedDescription))"
        }
    }
}

struct CameraPicker: UIViewControllerRepresentable {
    let onImage: (UIImage?) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ vc: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(onImage: onImage) }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate,
                             UINavigationControllerDelegate {
        let onImage: (UIImage?) -> Void
        init(onImage: @escaping (UIImage?) -> Void) { self.onImage = onImage }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            onImage(info[.originalImage] as? UIImage)
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            onImage(nil)
        }
    }
}
