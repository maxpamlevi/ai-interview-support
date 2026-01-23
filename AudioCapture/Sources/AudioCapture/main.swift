import Foundation
import CoreGraphics

// Simple entry point
if #available(macOS 13.0, *) {
    let recorder = AudioRecorder()
    recorder.start()
    
    // Keep running until interrupted
    RunLoop.main.run()
} else {
    print("Error: This tool requires macOS 12.3 or later.")
    exit(1)
}
