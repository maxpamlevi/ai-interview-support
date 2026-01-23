import Foundation
import ScreenCaptureKit
import AVFoundation

@available(macOS 13.0, *)
class AudioRecorder: NSObject, SCStreamOutput, SCStreamDelegate {
    
    private var stream: SCStream?
    private let targetAppName = "Google Chrome" // Hardcoded for simplified requirement, can be flexible
    
    func start() {
        Task {
            do {
                // macOS 13+ SCShareableContent.current might be the one, or excluding...
                // Trying shareableContent(excludingDesktopWindows:onScreenWindowsOnly:) which maps to getShareableContent
                // If this fails, we will try the basic current() if available.
                let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
                self.findAndCaptureApp(in: content)
            } catch {
                print("Error getting shareable content: \(error.localizedDescription)")
                exit(1)
            }
        }
    }
    
    private func findAndCaptureApp(in content: SCShareableContent) {
        // Find the target application (Google Chrome)
        // We look for any running application that matches our target name
        let targetApps = content.applications.filter { app in
            return app.applicationName == self.targetAppName
        }
        
        if targetApps.isEmpty {
            // Fallback: If chrome isn't found, maybe capture system wide? 
            // For now, let's just error out or try to find "Safari" or "Firefox" as backup if testing
            // or just print all apps to help debug
             print("Could not find application named '\(self.targetAppName)'. Available apps:")
             for app in content.applications {
                 print("- \(app.applicationName)")
             }
            exit(1)
        }
        
        // Use the first match
        let appToCapture = targetApps[0]
        print("Found app: \(appToCapture.applicationName) (PID: \(appToCapture.processID))")
        
        // Create a filter for this application
        // We want to capture audio from this app.
        // Note: Capturing just the app audio might not capture "Meet" output if it's treated oddly,
        // but usually catching the Chrome process works for browser audio.
        let filter = SCContentFilter(display: content.displays[0], including: [appToCapture], exceptingWindows: [])
        
        // Configure the stream for audio only
        let config = SCStreamConfiguration()
        config.capturesAudio = true
        // config.capturesShadows = false // Property may not exist
        config.showsCursor = false
        config.width = 100
        config.height = 100 // Minimal video size since we ignore it
        config.minimumFrameInterval = CMTime(value: 1, timescale: 60)
        
        // Set audio settings
        // We want raw PCM float 32 if possible to match standard ML models, or Int16
        // ScreenCaptureKit usually gives us the system format, usually 48kHz or 44.1kHz float.
        config.sampleRate = 48000
        config.channelCount = 1
        
        do {
            stream = SCStream(filter: filter, configuration: config, delegate: self)
            
            // Add output for audio
            try stream?.addStreamOutput(self, type: .audio, sampleHandlerQueue: DispatchQueue(label: "audio.queue"))
            
            // Start capture
            stream?.startCapture { error in
                if let error = error {
                    print("Error starting capture: \(error.localizedDescription)")
                    exit(1)
                }
                print("Capture started. Streaming PCM data to stdout...")
            }
            
        } catch {
            print("Failed to initialize stream: \(error.localizedDescription)")
            exit(1)
        }
    }
    
    // SCStreamOutput protocol
    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .audio else { return }
        
        // Extract audio data
        guard let blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer) else { return }
        
        var length = 0
        var totalLength = 0
        var dataPointer: UnsafeMutablePointer<Int8>?
        
        let status = CMBlockBufferGetDataPointer(blockBuffer, atOffset: 0, lengthAtOffsetOut: &length, totalLengthOut: &totalLength, dataPointerOut: &dataPointer)
        
        if status == kCMBlockBufferNoErr, let dataPointer = dataPointer {
            // Write raw bytes to stdout
            let data = Data(bytes: dataPointer, count: totalLength)
            
            // We use FileHandle.standardOutput.write checking for errors or broken pipe
            try? FileHandle.standardOutput.write(contentsOf: data)
        }
    }
    
    func stream(_ stream: SCStream, didStopWithError error: Error) {
        print("Stream stopped with error: \(error.localizedDescription)")
        exit(1)
    }
}
