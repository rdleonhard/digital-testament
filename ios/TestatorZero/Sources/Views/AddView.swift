import PhotosUI
import SwiftUI
import UIKit

// The "Write" tab — the fastest path into the corpus, and the only one
// with no AI call: type or dictate a memory, save. Below it, the camera
// path (which does use the vision model) for when you'd rather show than
// tell. Direct authorship is the point: no question, no chat, just you.

struct AddView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var subs: SubscriptionManager

    @State private var title = ""
    @State private var body_ = ""
    @State private var saved = false
    @FocusState private var focused: Bool

    // camera
    @State private var showCamera = false
    @State private var pickerItem: PhotosPickerItem?
    @State private var observing = false
    @State private var lastObservation: String?

    private var cameraAvailable: Bool {
        UIImagePickerController.isSourceTypeAvailable(.camera)
    }
    private var listening: Bool { voice.listening && voice.context == "compose" }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Write it down.")
                        .font(.system(.title2, design: .serif).weight(.medium))
                        .foregroundStyle(Theme.ink)
                    Text("A memory, plainly — no question, no AI. Just yours.")
                        .font(.subheadline).foregroundStyle(Theme.dim)

                    TextField("Title (optional)", text: $title)
                        .textFieldStyle(.plain).padding(12)
                        .background(Theme.panel, in: RoundedRectangle(cornerRadius: 10))
                        .foregroundStyle(Theme.ink)

                    ZStack(alignment: .topLeading) {
                        if body_.isEmpty {
                            Text("What do you want kept?")
                                .foregroundStyle(Theme.dim).padding(16)
                        }
                        TextEditor(text: $body_)
                            .focused($focused)
                            .frame(minHeight: 160)
                            .scrollContentBackground(.hidden)
                            .padding(8)
                            .foregroundStyle(Theme.ink)
                    }
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 12))

                    HStack(spacing: 14) {
                        Button {
                            if listening { voice.stopListening() }
                            else { try? voice.startListening(context: "compose") }
                        } label: {
                            Label(listening ? "listening…" : "dictate",
                                  systemImage: listening ? "mic.fill" : "mic")
                                .foregroundStyle(listening ? .red : Theme.gold)
                        }
                        Spacer()
                        Button {
                            store.commitMemory(title: title, narrative: body_)
                            title = ""; body_ = ""; focused = false
                            voice.stopListening()
                            withAnimation { saved = true }
                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) {
                                withAnimation { saved = false }
                            }
                        } label: {
                            Label("Keep it", systemImage: "flame")
                                .padding(.horizontal, 6)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(body_.trimmingCharacters(in: .whitespaces).isEmpty)
                    }

                    if saved {
                        Label("Kept. The flame is a little brighter.",
                              systemImage: "checkmark.seal")
                            .font(.footnote).foregroundStyle(Theme.gold)
                            .transition(.opacity)
                    }

                    Divider().overlay(Theme.dim).padding(.vertical, 8)

                    Text("Or show it something")
                        .font(.subheadline).foregroundStyle(Theme.dim)
                    if observing {
                        ProgressView("the avatar is looking…").tint(Theme.gold)
                    } else if let obs = lastObservation {
                        Text(obs).font(.footnote).foregroundStyle(Theme.ink)
                            .padding(14)
                            .background(Theme.panel, in: RoundedRectangle(cornerRadius: 12))
                        Text("kept as words only — the image is gone")
                            .font(.caption2).foregroundStyle(Theme.dim)
                    }
                    Group {
                        if cameraAvailable {
                            Button { showCamera = true } label: {
                                Label("Open the eye", systemImage: "camera")
                                    .frame(maxWidth: .infinity).padding(.vertical, 12)
                            }
                        } else {
                            PhotosPicker(selection: $pickerItem, matching: .images) {
                                Label("Choose a photo (no camera here)", systemImage: "photo")
                                    .frame(maxWidth: .infinity).padding(.vertical, 12)
                            }
                        }
                    }
                    .buttonStyle(.bordered)
                    .tint(Theme.gold)
                    .disabled(observing)
                }
                .padding(24)
            }
            .scrollDismissesKeyboard(.interactively)
            .background(Theme.bg)
            .navigationTitle("Write")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") { focused = false; hideKeyboard() }
                }
            }
            .onChange(of: voice.transcript) {
                if listening { body_ = voice.transcript }
            }
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
                       let img = UIImage(data: data) { await observe(img) }
                    pickerItem = nil
                }
            }
        }
    }

    private func observe(_ image: UIImage) async {
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subs.subscribed) else {
            lastObservation = VeniceError.needsEntitlement.localizedDescription
            return
        }
        observing = true
        defer { observing = false }
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
        ) { onImage(info[.originalImage] as? UIImage) }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            onImage(nil)
        }
    }
}
