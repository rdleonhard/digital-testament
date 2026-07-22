import AVFoundation
import Speech
import SwiftUI

// The avatar's ears and voice.
// Ears: on-device speech recognition (hold the mic, speak a memory).
// Voice: AVSpeechSynthesizer — and when the subject has recorded an iOS
// Personal Voice (Settings > Accessibility > Personal Voice), the avatar
// speaks IN THEIR OWN VOICE, cloned on-device by Apple. That is the
// voicebox idea done privacy-first: the testator records themselves in
// life; the avatar inherits the voice. Server-side cloning stays on the
// roadmap for richer prosody.

@MainActor
final class VoiceManager: NSObject, ObservableObject {
    @Published var transcript = ""
    @Published var listening = false
    @Published var speaking = false
    @Published var personalVoiceReady = false
    // Which screen owns the current dictation, so one tab's speech never
    // leaks into another's text field (they share this one manager).
    @Published var context = ""

    private let synth = AVSpeechSynthesizer()
    private let recognizer = SFSpeechRecognizer()
    private var task: SFSpeechRecognitionTask?
    private let engine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?

    override init() {
        super.init()
        synth.delegate = self
    }

    func requestPermissions() {
        SFSpeechRecognizer.requestAuthorization { _ in }
        AVAudioApplication.requestRecordPermission { _ in }
        AVSpeechSynthesizer.requestPersonalVoiceAuthorization { [weak self] status in
            Task { @MainActor in
                self?.personalVoiceReady = (status == .authorized) &&
                    !AVSpeechSynthesisVoice.speechVoices()
                        .filter { $0.voiceTraits.contains(.isPersonalVoice) }.isEmpty
            }
        }
    }

    // MARK: ears

    func startListening(context: String = "") throws {
        stopSpeaking()
        self.context = context
        transcript = ""
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try session.setActive(true, options: .notifyOthersOnDeactivation)
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.requiresOnDeviceRecognition = false
        request = req
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { buf, _ in
            req.append(buf)
        }
        engine.prepare()
        try engine.start()
        listening = true
        task = recognizer?.recognitionTask(with: req) { [weak self] result, error in
            Task { @MainActor in
                if let r = result { self?.transcript = r.bestTranscription.formattedString }
                if error != nil { self?.stopListening() }
            }
        }
    }

    func stopListening() {
        engine.stop()
        engine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.cancel()
        task = nil
        listening = false
    }

    // MARK: voice

    func speak(_ text: String) {
        stopSpeaking()
        let utt = AVSpeechUtterance(string: text)
        if personalVoiceReady,
           let personal = AVSpeechSynthesisVoice.speechVoices()
               .first(where: { $0.voiceTraits.contains(.isPersonalVoice) }) {
            utt.voice = personal
        } else {
            utt.voice = AVSpeechSynthesisVoice(language: "en-US")
        }
        utt.rate = 0.48
        speaking = true
        synth.speak(utt)
    }

    func stopSpeaking() {
        synth.stopSpeaking(at: .immediate)
        speaking = false
    }
}

extension VoiceManager: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(_ s: AVSpeechSynthesizer,
                                       didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in self.speaking = false }
    }
    nonisolated func speechSynthesizer(_ s: AVSpeechSynthesizer,
                                       didCancel utterance: AVSpeechUtterance) {
        Task { @MainActor in self.speaking = false }
    }
}
